"""
Firestore Database Layer for Universities Knowledge Base.
Provides CRUD operations and search functionality for university profiles.
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from google.cloud import firestore

import major_catalog

logger = logging.getLogger(__name__)

# Collection name
COLLECTION_NAME = "universities"
# Per-year snapshots live under universities/{id}/versions/{year}.
# The main doc always serves the latest ingested cycle year (ADR 0002).
VERSIONS_SUBCOLLECTION = "versions"
# Global majors catalog (#303): union of majors across all profiles, one doc.
MAJOR_CATALOG_COLLECTION = "major_catalog"
MAJOR_CATALOG_DOC = "current"


class FirestoreDB:
    """Firestore database client for university profiles."""

    def __init__(self):
        self.db = firestore.Client()
        self.collection = self.db.collection(COLLECTION_NAME)
        logger.info(f"[Firestore] Client initialized for collection: {COLLECTION_NAME}")

    def _versions(self, university_id: str):
        return self.collection.document(university_id).collection(VERSIONS_SUBCOLLECTION)

    def get_university(self, university_id: str, year: Optional[int] = None) -> Optional[Dict]:
        """Get a university by ID — the current doc, or a specific cycle year."""
        try:
            if year is not None:
                doc = self._versions(university_id).document(str(year)).get()
            else:
                doc = self.collection.document(university_id).get()
            if doc.exists:
                data = doc.to_dict()
                data['university_id'] = university_id
                return data
            return None
        except Exception as e:
            logger.error(f"Get university failed: {e}")
            return None

    def get_available_years(self, university_id: str) -> List[int]:
        """The main doc's available_years via a field-mask read (near-free)."""
        try:
            doc = self.collection.document(university_id).get(field_paths=['available_years'])
            if doc.exists:
                return (doc.to_dict() or {}).get('available_years') or []
            return []
        except Exception as e:
            logger.error(f"Get available years failed: {e}")
            return []

    def list_version_docs(self, university_id: str) -> List[Dict]:
        """Full cycle-year snapshot docs for a university, newest first."""
        try:
            docs = []
            for doc in self._versions(university_id).stream():
                data = doc.to_dict() or {}
                data['university_id'] = university_id
                if data.get('data_year') is None:
                    try:
                        data['data_year'] = int(doc.id)
                    except (TypeError, ValueError):
                        pass
                docs.append(data)
            docs.sort(key=lambda d: (d.get('data_year') is not None,
                                     d.get('data_year') or 0), reverse=True)
            return docs
        except Exception as e:
            logger.error(f"List version docs failed: {e}")
            return []

    def list_university_versions(self, university_id: str) -> List[Dict]:
        """List stored cycle-year snapshots for a university, newest first."""
        try:
            versions = []
            for doc in self._versions(university_id).stream():
                data = doc.to_dict() or {}
                year = data.get('data_year')
                if year is None:
                    try:
                        year = int(doc.id)
                    except (TypeError, ValueError):
                        continue  # junk doc id — skip it, don't hide the rest
                versions.append({
                    "year": year,
                    "official_name": data.get('official_name'),
                    "indexed_at": data.get('indexed_at'),
                    "last_updated": data.get('last_updated'),
                })
            versions.sort(key=lambda v: v['year'], reverse=True)
            return versions
        except Exception as e:
            logger.error(f"List versions failed: {e}")
            return []
    
    def list_universities(
        self, 
        limit: int = 30, 
        offset: int = 0,
        sort_by: str = "us_news_rank",
        search_term: str = None,
        state: str = None,
        max_acceptance_rate: float = None,
        soft_fit_category: str = None,
        university_type: str = None
    ) -> Dict:
        """
        List universities with pagination, search, and filter support.
        
        Args:
            limit: Number of results per page (default 30)
            offset: Number of results to skip (for pagination)
            sort_by: Field to sort by (us_news_rank, acceptance_rate, official_name)
            search_term: Optional search string to filter by university name
            state: Optional state code to filter by (e.g., 'CA', 'NY')
            max_acceptance_rate: Optional max acceptance rate to filter by
            soft_fit_category: Optional fit category ('Safety', 'Target', 'Reach')
            university_type: Optional type ('Public' or 'Private')
        
        Returns:
            Dict with 'universities' list and 'total' count
        """
        try:
            # First, get all docs
            all_docs = list(self.collection.stream())
            
            # Filter by search term if provided
            if search_term:
                search_lower = search_term.lower()
                all_docs = [
                    doc for doc in all_docs 
                    if search_lower in (doc.to_dict().get('official_name') or '').lower()
                ]
            
            # Filter by state if provided
            if state:
                state_upper = state.upper()
                # Handle both 2-letter codes and full state names
                all_docs = [
                    doc for doc in all_docs
                    if self._normalize_state(doc.to_dict().get('location', {}).get('state')) == state_upper
                ]
            
            # Filter by max acceptance rate if provided
            if max_acceptance_rate is not None:
                all_docs = [
                    doc for doc in all_docs
                    if (doc.to_dict().get('acceptance_rate') or 100) <= max_acceptance_rate
                ]
            
            # Filter by soft fit category if provided
            if soft_fit_category:
                all_docs = [
                    doc for doc in all_docs
                    if doc.to_dict().get('soft_fit_category') == soft_fit_category
                ]
            
            # Filter by university type (Public/Private) if provided
            if university_type:
                all_docs = [
                    doc for doc in all_docs
                    if doc.to_dict().get('location', {}).get('type') == university_type
                ]
            
            total = len(all_docs)
            
            # Sort documents based on sort_by parameter
            if sort_by == "us_news_rank":
                all_docs_sorted = sorted(
                    all_docs, 
                    key=lambda d: (
                        d.to_dict().get('us_news_rank') is None,
                        d.to_dict().get('us_news_rank') or 9999
                    )
                )
            elif sort_by == "acceptance_rate":
                all_docs_sorted = sorted(
                    all_docs,
                    key=lambda d: (
                        d.to_dict().get('acceptance_rate') is None,
                        d.to_dict().get('acceptance_rate') or 100
                    )
                )
            elif sort_by == "official_name":
                all_docs_sorted = sorted(
                    all_docs,
                    key=lambda d: (d.to_dict().get('official_name') or 'ZZZ').lower()
                )
            else:
                all_docs_sorted = all_docs
            
            # Apply pagination
            paginated_docs = all_docs_sorted[offset:offset + limit]
            
            universities = []
            for doc in paginated_docs:
                data = doc.to_dict()
                data['university_id'] = doc.id
                universities.append(data)
            
            return {
                "universities": universities,
                "total": total,
                "limit": limit,
                "offset": offset
            }
        except Exception as e:
            logger.error(f"List universities failed: {e}")
            return {"universities": [], "total": 0, "limit": limit, "offset": offset}
    
    def _normalize_state(self, state: str) -> str:
        """Normalize state to 2-letter code."""
        if not state:
            return None
        # If already 2-letter code
        if len(state) == 2 and state == state.upper():
            return state
        # Map full names to codes
        state_map = {
            'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA',
            'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE', 'Florida': 'FL', 'Georgia': 'GA',
            'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA',
            'Kansas': 'KS', 'Kentucky': 'KY', 'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD',
            'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
            'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ',
            'New Mexico': 'NM', 'New York': 'NY', 'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH',
            'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI', 'South Carolina': 'SC',
            'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT',
            'Virginia': 'VA', 'Washington': 'WA', 'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY',
            'District of Columbia': 'DC'
        }
        return state_map.get(state, state.upper() if state else None)
    
    def save_university(self, university_id: str, data: Dict, year: int) -> Dict:
        """Save a university snapshot for `year` and promote it to the main
        doc when it is the newest cycle (ADR 0002).

        The snapshot under versions/{year} is always written (idempotent
        per-year refresh). The main doc is overwritten only when
        year >= the main doc's data_year; a legacy main doc without
        data_year is treated as older than any versioned ingest.

        Returns {"saved": bool, "promoted": bool, "available_years": [int]}.
        """
        try:
            data['last_updated'] = datetime.now(timezone.utc).isoformat()
            data['data_year'] = year

            self._versions(university_id).document(str(year)).set(data)

            main_ref = self.collection.document(university_id)
            main_doc = main_ref.get()
            existing = main_doc.to_dict() if main_doc.exists else None
            current_year = (existing or {}).get('data_year')

            # A legacy (pre-versioning) main doc is about to be taken over —
            # snapshot it first so its data isn't lost. Its true vintage is
            # unknown; year-1 is the best guess and keeps it readable.
            if existing is not None and current_year is None:
                legacy_year = year - 1
                legacy_ref = self._versions(university_id).document(str(legacy_year))
                if not legacy_ref.get().exists:
                    legacy_snapshot = dict(existing)
                    legacy_snapshot['data_year'] = legacy_year
                    # Honest provenance for readers: this year is a guess,
                    # not a verified collection cycle (year_history surfaces it).
                    legacy_snapshot['vintage_estimated'] = True
                    legacy_ref.set(legacy_snapshot)
                    logger.info(
                        f"Auto-archived legacy doc {university_id} as year {legacy_year}"
                    )

            promoted = current_year is None or year >= current_year

            years = {v['year'] for v in self.list_university_versions(university_id)}
            years.add(year)
            available_years = sorted(years)

            if promoted:
                main_data = dict(data)
                main_data['available_years'] = available_years
                main_ref.set(main_data)
            else:
                main_ref.update({'available_years': available_years})

            logger.info(
                f"Saved university {university_id} year={year} "
                f"promoted={promoted} years={available_years}"
            )
            return {"saved": True, "promoted": promoted, "available_years": available_years}
        except Exception as e:
            logger.error(f"Save university failed: {e}")
            return {"saved": False, "promoted": False, "available_years": []}

    def delete_university(self, university_id: str, year: Optional[int] = None) -> bool:
        """Delete a university, or one cycle-year snapshot.

        Whole-university delete removes every version snapshot plus the main
        doc. Deleting the year currently serving the main doc promotes the
        latest remaining version; if none remain, the main doc goes too.
        """
        try:
            main_ref = self.collection.document(university_id)

            if year is None:
                for doc in self._versions(university_id).stream():
                    doc.reference.delete()
                main_ref.delete()
                logger.info(f"Deleted university: {university_id} (all versions)")
                return True

            self._versions(university_id).document(str(year)).delete()

            main_doc = main_ref.get()
            current_year = (main_doc.to_dict() or {}).get('data_year') if main_doc.exists else None
            remaining = self.list_university_versions(university_id)
            available_years = sorted(v['year'] for v in remaining)

            if current_year == year:
                if remaining:
                    latest = self.get_university(university_id, year=remaining[0]['year'])
                    latest.pop('university_id', None)
                    latest['available_years'] = available_years
                    main_ref.set(latest)
                else:
                    main_ref.delete()
            elif main_doc.exists:
                main_ref.update({'available_years': available_years})

            logger.info(f"Deleted university {university_id} year={year}")
            return True
        except Exception as e:
            logger.error(f"Delete university failed: {e}")
            return False
    
    def batch_get_universities(self, university_ids: List[str]) -> List[Dict]:
        """Get multiple universities by ID."""
        try:
            if not university_ids:
                return []
            
            # Firestore doesn't have native batch get with IDs, use document references
            universities = []
            for uid in university_ids:
                doc = self.collection.document(uid).get()
                if doc.exists:
                    data = doc.to_dict()
                    data['university_id'] = doc.id
                    universities.append(data)
            
            return universities
        except Exception as e:
            logger.error(f"Batch get universities failed: {e}")
            return []
    
    def search_universities(
        self, 
        query: str, 
        limit: int = 10, 
        filters: Dict = None, 
        exclude_ids: List[str] = None,
        sort_by: str = "relevance"
    ) -> List[Dict]:
        """
        Search universities using text matching and filters.
        
        Note: Firestore doesn't support full-text search natively.
        This implementation:
        1. Fetches all universities (or filtered subset)
        2. Filters in-memory by matching query against searchable fields
        3. Sorts results
        
        For production, consider:
        - Algolia/Firebase Extensions for full-text search
        - Cloud Firestore vector search (if available)
        - Pre-computed keyword indexes
        """
        try:
            query_lower = query.lower().strip()
            
            # Start with base query
            db_query = self.collection
            
            # Apply Firestore-native filters (before fetching)
            if filters:
                if filters.get('state'):
                    db_query = db_query.where('location.state', '==', filters['state'])
                if filters.get('type'):
                    db_query = db_query.where('location.type', '==', filters['type'])
                if filters.get('market_position'):
                    db_query = db_query.where('market_position', '==', filters['market_position'])
            
            # Fetch documents
            docs = db_query.limit(500).stream()  # Fetch more for in-memory filtering
            
            results = []
            for doc in docs:
                data = doc.to_dict()
                university_id = doc.id
                
                # Skip excluded IDs
                if exclude_ids and university_id in exclude_ids:
                    continue
                
                # Apply acceptance rate filters (ranges need in-memory filtering)
                if filters:
                    acceptance_rate = data.get('acceptance_rate')
                    if acceptance_rate is not None:
                        if filters.get('acceptance_rate_max') and acceptance_rate > filters['acceptance_rate_max']:
                            continue
                        if filters.get('acceptance_rate_min') and acceptance_rate < filters['acceptance_rate_min']:
                            continue
                
                # Text matching
                score = self._calculate_match_score(data, query_lower)
                
                if score > 0:
                    data['university_id'] = university_id
                    data['score'] = score
                    results.append(data)
            
            # Sort results
            if sort_by in ["rank", "us_news_rank"]:
                # Sort by US News rank (ascending, nulls last)
                results.sort(key=lambda x: (x.get('us_news_rank') is None, x.get('us_news_rank') or 9999))
            elif sort_by in ["selectivity", "acceptance_rate"]:
                # Sort by acceptance rate (ascending, nulls last)
                results.sort(key=lambda x: (x.get('acceptance_rate') is None, x.get('acceptance_rate') or 100))
            else:
                # Sort by relevance score (descending)
                results.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search universities failed: {e}", exc_info=True)
            return []
    
    def _calculate_match_score(self, data: Dict, query_lower: str) -> float:
        """
        Calculate relevance score for a university based on query match.
        Returns 0 if no match, higher scores for better matches.
        """
        score = 0.0
        query_terms = query_lower.split()
        
        # Check official name (highest weight)
        official_name = (data.get('official_name') or '').lower()
        for term in query_terms:
            if term in official_name:
                score += 10.0
                if official_name.startswith(term):
                    score += 5.0
        
        # Check university_id
        university_id = (data.get('university_id') or '').lower()
        for term in query_terms:
            if term in university_id:
                score += 8.0
        
        # Check searchable_text (pre-computed during ingest)
        searchable_text = (data.get('searchable_text') or '').lower()
        for term in query_terms:
            if term in searchable_text:
                score += 2.0
        
        # Check keywords array (if present)
        keywords = data.get('keywords', [])
        if isinstance(keywords, list):
            keywords_str = ' '.join(keywords).lower()
            for term in query_terms:
                if term in keywords_str:
                    score += 3.0
        
        # Check location
        location = data.get('location', {})
        if isinstance(location, dict):
            city = (location.get('city') or '').lower()
            state = (location.get('state') or '').lower()
            for term in query_terms:
                if term in city or term in state:
                    score += 2.0
        
        # Check market position
        market_position = (data.get('market_position') or '').lower()
        for term in query_terms:
            if term in market_position:
                score += 1.0
        
        return score
    
    # ==================== MAJOR CATALOG (#303) ====================

    def _catalog_ref(self):
        return self.db.collection(MAJOR_CATALOG_COLLECTION).document(MAJOR_CATALOG_DOC)

    def get_major_catalog(self) -> Optional[Dict]:
        """The raw catalog doc (majors keyed by normalized name), or None."""
        try:
            doc = self._catalog_ref().get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            logger.error(f"Get major catalog failed: {e}")
            return None

    def save_major_catalog(self, catalog: Dict) -> bool:
        """Overwrite the catalog doc (full rebuild — backfill script)."""
        try:
            catalog['updated_at'] = datetime.now(timezone.utc).isoformat()
            self._catalog_ref().set(catalog)
            return True
        except Exception as e:
            logger.error(f"Save major catalog failed: {e}")
            return False

    def update_major_catalog_for_school(self, university_id: str, profile: Dict) -> bool:
        """Best-effort incremental upsert of one school's majors into the
        catalog (idempotent). Returns False on failure — callers must NOT let
        a catalog error break the ingest."""
        try:
            current = self.get_major_catalog()
            updated = major_catalog.add_school(current, university_id, profile)
            updated['updated_at'] = datetime.now(timezone.utc).isoformat()
            self._catalog_ref().set(updated)
            return True
        except Exception as e:
            logger.warning(f"[CATALOG] incremental update failed for {university_id}: {e}")
            return False

    def health_check(self) -> Dict:
        """Check Firestore connectivity."""
        try:
            # Try to read a document to verify connection
            list(self.collection.limit(1).stream())
            return {
                "success": True,
                "firestore": True,
                "collection": COLLECTION_NAME
            }
        except Exception as e:
            return {
                "success": False,
                "firestore": False,
                "error": str(e)
            }


# ========== SINGLETON ==========
_db_instance = None


def get_db() -> FirestoreDB:
    """Get or create Firestore instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = FirestoreDB()
    return _db_instance
