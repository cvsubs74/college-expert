
import logging
import sys
import os

# Add parent directory to path to import tools
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from tools.tools import search_universities
from tools.acronyms import ACRONYM_MAP

# Setup basic logging
logging.basicConfig(level=logging.INFO)

def test_acronym_resolution():
    """Test that acronyms resolve to specific universities."""
    
    test_cases = [
        ("USC", "university_of_southern_california"),
        ("ucla", "university_of_california_los_angeles"),
        ("MIT", "massachusetts_institute_of_technology"),
        ("Gt", "georgia_institute_of_technology")
    ]
    
    passed = 0
    total = len(test_cases)
    
    print("\nStarting Acronym Resolution Tests...")
    print("="*60)
    
    for query, expected_id in test_cases:
        print(f"\nTesting query: '{query}'")
        
        # Call search_universities
        # Note: This requires the knowledge base URL to be accessible
        result = search_universities(query)
        
        if not result['success']:
            print(f"❌ Search failed: {result.get('error')}")
            continue
            
        universities = result.get('universities', [])
        
        if not universities:
            print("❌ No universities found")
            continue
            
        first_uni = universities[0]
        actual_id = first_uni.get('university_id')
        
        print(f"   Resolved ID: {actual_id}")
        print(f"   Name: {first_uni.get('official_name')}")
        print(f"   Search Type: {result.get('search_type')}")
        
        if actual_id == expected_id and result.get('search_type') == 'acronym_resolution':
            # Verify profile data is populated
            strategic_profile = first_uni.get('strategic_profile', {})
            if strategic_profile:
                print(f"   ✅ Strategic Profile found (keys: {list(strategic_profile.keys())[:3]}...)")
                print("✅ PASS")
                passed += 1
            else:
                print("❌ FAIL - Strategic Profile is empty (Data extraction bug?)")
        else:
            print(f"❌ FAIL - Expected {expected_id}, got {actual_id}")
            
    print("="*60)
    print(f"Summary: {passed}/{total} passed")

if __name__ == "__main__":
    test_acronym_resolution()
