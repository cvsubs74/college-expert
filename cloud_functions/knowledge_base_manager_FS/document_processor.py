"""
Document processor for extracting structured metadata from university documents.
Uses LLM to convert unstructured text to structured schema and stores in Firestore.
"""

import json
from google import genai
from google.cloud import firestore
from typing import Dict, Any

# University admissions schema
UNIVERSITY_SCHEMA = {
    "title": "University_Admissions_and_Academic_Profile",
    "description": "A comprehensive data structure for institutional policies, admissions statistics, and capacity management strategies of a single university.",
    "type": "object",
    "properties": {
        "university_identity": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The full legal name of the institution"},
                "location": {"type": "string"},
                "type": {"type": "string", "description": "Public, Private, Land-Grant, Public Ivy, etc."},
                "academic_calendar": {"type": "string", "description": "Semester, Quarter, etc."},
                "core_admissions_philosophy": {"type": "string"}
            }
        },
        "admissions_overview": {
            "type": "object",
            "properties": {
                "overall_acceptance_rate_recent": {"type": "string"},
                "resident_vs_nonresident_policy": {"type": "string"},
                "testing_policy": {"type": "string"},
                "holistic_review_primary_differentiators": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "historical_admissions_data": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "entry_term": {"type": "string"},
                    "total_applications": {"type": "integer"},
                    "total_admits": {"type": "integer"},
                    "acceptance_rate": {"type": "string"},
                    "enrolled_sat_mid_50_percent": {"type": "string"},
                    "enrolled_gpa_mid_50_percent_weighted": {"type": "string"},
                    "enrolled_gpa_mid_50_percent_unweighted": {"type": "string"}
                }
            }
        },
        "academic_structure": {
            "type": "object",
            "properties": {
                "number_of_undergraduate_colleges": {"type": "integer"},
                "colleges_and_schools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "admission_pathway": {"type": "string"},
                            "degrees_offered": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "majors_inventory": {"type": "array", "items": {"type": "string"}},
                "minors_inventory": {"type": "array", "items": {"type": "string"}}
            }
        },
        "major_capacity_management_policies": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "major_name": {"type": "string"},
                    "parent_college": {"type": "string"},
                    "selectivity_type": {"type": "string"},
                    "estimated_freshman_admit_rate": {"type": "string"},
                    "admission_commitment": {"type": "string"},
                    "binary_or_de_facto_prerequisites": {"type": "array", "items": {"type": "string"}},
                    "talent_or_qualitative_supplement_required": {"type": "string"},
                    "internal_transfer_policy": {
                        "type": "object",
                        "properties": {
                            "pathway_existence": {"type": "string"},
                            "mechanism": {"type": "string"},
                            "selection_criteria_notes": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        },
        "credit_articulation_policies": {
            "type": "object",
            "properties": {
                "overarching_philosophy": {"type": "string"},
                "maximum_transfer_units": {"type": "string"},
                "dual_enrollment_restrictions": {"type": "string"},
                "ap_credit_articulations_notes": {"type": "string"},
                "credit_articulation_tools": {"type": "array", "items": {"type": "string"}}
            }
        },
        "financial_aid_and_cost": {
            "type": "object",
            "properties": {
                "cost_of_attendance_itemized_2025_2026": {
                    "type": "object",
                    "properties": {
                        "resident_total_estimated_coa": {"type": "string"},
                        "nonresident_total_estimated_coa": {"type": "string"},
                        "nonresident_supplemental_tuition": {"type": "string"}
                    }
                },
                "financial_aid_philosophy": {"type": "string"},
                "merit_aid_policy": {"type": "string"},
                "flagship_scholarship_programs": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "basis": {"type": "string"},
                            "key_benefits": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                }
            }
        },
        "application_deadlines": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "milestone": {"type": "string"},
                    "deadline_date": {"type": "string"},
                    "plan_type": {"type": "string"},
                    "significance": {"type": "string"}
                }
            }
        }
    },
    "required": [
        "university_identity",
        "admissions_overview",
        "academic_structure",
        "major_capacity_management_policies",
        "financial_aid_and_cost",
        "application_deadlines"
    ]
}


class DocumentProcessor:
    """Processes documents to extract structured metadata using LLM."""
    
    def __init__(self, gemini_api_key: str, firestore_collection: str = "university_metadata"):
        """Initialize processor with Gemini client and Firestore."""
        self.client = genai.Client(
            api_key=gemini_api_key,
            http_options={'api_version': 'v1alpha'}
        )
        self.db = firestore.Client()
        self.collection = firestore_collection
        
    def extract_structured_metadata(self, document_text: str, filename: str) -> Dict[str, Any]:
        """
        Use LLM to extract structured metadata from unstructured document text.
        
        Args:
            document_text: Raw text extracted from the document
            filename: Name of the document file
            
        Returns:
            Structured metadata conforming to UNIVERSITY_SCHEMA
        """
        prompt = f"""
        You are a data extraction specialist. Extract structured information from the following university document.
        
        **DOCUMENT:** {filename}
        
        **TEXT:**
        {document_text[:50000]}  # Limit to first 50k chars to avoid token limits
        
        **YOUR TASK:**
        Extract ALL relevant information from this document and structure it according to the provided schema.
        
        **CRITICAL INSTRUCTIONS:**
        1. Extract university identity (name, location, type, calendar, admissions philosophy)
        2. Extract admissions overview (acceptance rates, testing policy, holistic factors)
        3. Extract historical admissions data if available (applications, admits, SAT/GPA ranges)
        4. Extract academic structure (colleges, schools, majors, minors)
        5. Extract major capacity management policies (selective majors, admission requirements, transfer policies)
        6. Extract credit articulation policies (AP credit, transfer units, dual enrollment)
        7. Extract financial aid information (cost of attendance, aid philosophy, scholarships)
        8. Extract application deadlines (ED, EA, RD dates)
        
        **IMPORTANT:**
        - If information is not available in the document, use null or empty arrays
        - Be precise with numbers and percentages
        - Extract exact quotes for policies when possible
        - Maintain data accuracy - do not invent information
        
        **OUTPUT:**
        Return a valid JSON object conforming to the schema.
        """
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0.1,  # Low temperature for factual extraction
                    response_mime_type="application/json",
                    response_schema=UNIVERSITY_SCHEMA
                )
            )
            
            # Parse the JSON response
            metadata = json.loads(response.text)
            
            # Add document metadata
            metadata["_document_metadata"] = {
                "filename": filename,
                "processed_at": firestore.SERVER_TIMESTAMP,
                "extraction_model": "gemini-2.5-flash"
            }
            
            return metadata
            
        except Exception as e:
            print(f"[EXTRACTION ERROR] Failed to extract metadata from {filename}: {str(e)}")
            # Return minimal metadata on error
            return {
                "university_identity": {"name": "Unknown"},
                "admissions_overview": {},
                "academic_structure": {},
                "major_capacity_management_policies": [],
                "financial_aid_and_cost": {},
                "application_deadlines": [],
                "_document_metadata": {
                    "filename": filename,
                    "processed_at": firestore.SERVER_TIMESTAMP,
                    "extraction_error": str(e)
                }
            }
    
    def store_metadata_in_firestore(self, metadata: Dict[str, Any], document_id: str) -> bool:
        """
        Store structured metadata in Firestore.
        
        Args:
            metadata: Structured metadata dictionary
            document_id: Unique identifier for the document
            
        Returns:
            True if successful, False otherwise
        """
        try:
            doc_ref = self.db.collection(self.collection).document(document_id)
            doc_ref.set(metadata)
            print(f"[FIRESTORE] Successfully stored metadata for document: {document_id}")
            return True
        except Exception as e:
            print(f"[FIRESTORE ERROR] Failed to store metadata: {str(e)}")
            return False
    
    def process_and_store_document(self, document_text: str, filename: str, document_id: str) -> Dict[str, Any]:
        """
        Complete pipeline: extract metadata and store in Firestore.
        
        Args:
            document_text: Raw text from document
            filename: Original filename
            document_id: Unique identifier
            
        Returns:
            Extracted metadata dictionary
        """
        print(f"[PROCESSOR] Processing document: {filename}")
        
        # Step 1: Extract structured metadata using LLM
        metadata = self.extract_structured_metadata(document_text, filename)
        
        # Step 2: Store in Firestore
        success = self.store_metadata_in_firestore(metadata, document_id)
        
        if success:
            print(f"[PROCESSOR] Successfully processed and stored: {filename}")
        else:
            print(f"[PROCESSOR] Processed but failed to store: {filename}")
        
        return metadata
