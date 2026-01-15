#!/usr/bin/env python3
"""
Migrate University Data from Elasticsearch to Firestore

This script fetches all university profiles from the ES-based knowledge base
and ingests them into the new Firestore-based knowledge base.

Usage:
    python migrate_es_to_firestore.py
    
    # Dry run (show what would be migrated without actually doing it)
    python migrate_es_to_firestore.py --dry-run
    
    # Migrate specific universities only
    python migrate_es_to_firestore.py --ids stanford_university mit
"""

import argparse
import json
import logging
import requests
import sys
from typing import List, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Endpoints
ES_KNOWLEDGE_BASE_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"
FIRESTORE_KNOWLEDGE_BASE_URL = "https://knowledge-base-manager-universities-v2-pfnwjfp26a-ue.a.run.app"


def fetch_all_universities_from_es() -> List[Dict]:
    """Fetch all universities from the ES-based knowledge base."""
    logger.info(f"Fetching universities from ES: {ES_KNOWLEDGE_BASE_URL}")
    
    try:
        response = requests.get(ES_KNOWLEDGE_BASE_URL, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            universities = data.get('universities', [])
            logger.info(f"Found {len(universities)} universities in ES")
            return universities
        else:
            logger.error(f"ES API returned error: {data.get('error')}")
            return []
    except Exception as e:
        logger.error(f"Failed to fetch from ES: {e}")
        return []


def fetch_university_profile_from_es(university_id: str) -> Dict:
    """Fetch full profile for a specific university from ES."""
    logger.info(f"Fetching profile for: {university_id}")
    
    try:
        response = requests.get(
            ES_KNOWLEDGE_BASE_URL, 
            params={"id": university_id},
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('success') and data.get('university'):
            university = data['university']
            # The full profile is nested under 'profile'
            return university.get('profile', university)
        else:
            logger.warning(f"Could not fetch profile for {university_id}: {data.get('error')}")
            return None
    except Exception as e:
        logger.error(f"Failed to fetch profile for {university_id}: {e}")
        return None


def ingest_to_firestore(profile: Dict) -> bool:
    """Ingest a university profile into the Firestore knowledge base."""
    university_id = profile.get('_id')
    if not university_id:
        logger.error("Profile missing '_id' field")
        return False
    
    logger.info(f"Ingesting to Firestore: {university_id}")
    
    try:
        response = requests.post(
            FIRESTORE_KNOWLEDGE_BASE_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=60
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get('success'):
            logger.info(f"✓ Successfully ingested: {university_id}")
            return True
        else:
            logger.error(f"✗ Ingest failed for {university_id}: {data.get('error')}")
            return False
    except Exception as e:
        logger.error(f"✗ Failed to ingest {university_id}: {e}")
        return False


def migrate_universities(university_ids: List[str] = None, dry_run: bool = False):
    """
    Migrate universities from ES to Firestore.
    
    Args:
        university_ids: List of specific university IDs to migrate, or None for all
        dry_run: If True, don't actually ingest, just show what would be done
    """
    # Fetch list of universities
    universities = fetch_all_universities_from_es()
    
    if not universities:
        logger.error("No universities found in ES")
        return
    
    # Filter to specific IDs if provided
    if university_ids:
        universities = [u for u in universities if u.get('university_id') in university_ids]
        logger.info(f"Filtered to {len(universities)} specified universities")
    
    if dry_run:
        logger.info("=== DRY RUN MODE - No data will be ingested ===")
    
    # Track results
    success_count = 0
    fail_count = 0
    
    for i, university in enumerate(universities, 1):
        university_id = university.get('university_id')
        official_name = university.get('official_name', university_id)
        
        logger.info(f"\n[{i}/{len(universities)}] Processing: {official_name}")
        
        if dry_run:
            logger.info(f"  Would migrate: {university_id}")
            success_count += 1
            continue
        
        # Fetch full profile from ES
        profile = fetch_university_profile_from_es(university_id)
        
        if not profile:
            logger.warning(f"  Skipping {university_id} - could not fetch profile")
            fail_count += 1
            continue
        
        # Ensure _id is set
        if '_id' not in profile:
            profile['_id'] = university_id
        
        # Ingest to Firestore
        if ingest_to_firestore(profile):
            success_count += 1
        else:
            fail_count += 1
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*60)
    logger.info(f"Total universities: {len(universities)}")
    logger.info(f"Successfully migrated: {success_count}")
    logger.info(f"Failed: {fail_count}")
    
    if dry_run:
        logger.info("\nThis was a DRY RUN. No data was actually migrated.")
        logger.info("Run without --dry-run to perform the actual migration.")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate university data from Elasticsearch to Firestore"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually doing it"
    )
    parser.add_argument(
        "--ids",
        nargs="+",
        help="Specific university IDs to migrate (space-separated)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("University Data Migration: ES → Firestore")
    logger.info("="*60)
    logger.info(f"Source (ES): {ES_KNOWLEDGE_BASE_URL}")
    logger.info(f"Target (Firestore): {FIRESTORE_KNOWLEDGE_BASE_URL}")
    logger.info("")
    
    migrate_universities(
        university_ids=args.ids,
        dry_run=args.dry_run
    )


if __name__ == "__main__":
    main()
