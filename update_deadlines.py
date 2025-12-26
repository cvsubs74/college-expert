#!/usr/bin/env python3
"""
Update application deadlines in all university JSON files to 2025-2026 cycle.

Standard deadline dates:
- Early Decision (ED): November 1, 2025 (some Nov 15)
- Early Action (EA): November 1, 2025 (some Nov 15)
- Restrictive Early Action (REA): November 1, 2025
- Early Decision II (ED2): January 1, 2026 (some Jan 5 or 15)
- Regular Decision (RD): January 1-15, 2026 (varies by school)
- Rolling: No fixed deadline
"""

import json
import os
import glob
from datetime import datetime

RESEARCH_DIR = "agents/university_profile_collector/research"

# Mapping of plan types to correct 2025-2026 dates
def get_updated_date(plan_type: str) -> str:
    """Get the correct 2025-2026 date based on plan type."""
    plan_lower = plan_type.lower()
    
    if 'early decision ii' in plan_lower or 'ed2' in plan_lower or 'ed ii' in plan_lower:
        return "2026-01-05"
    elif 'early decision' in plan_lower or plan_lower.startswith('ed'):
        return "2025-11-01"
    elif 'restrictive early action' in plan_lower or 'rea' in plan_lower:
        return "2025-11-01"
    elif 'early action' in plan_lower or plan_lower.startswith('ea'):
        return "2025-11-01"
    elif 'regular' in plan_lower or 'rd' in plan_lower:
        return "2026-01-15"
    elif 'rolling' in plan_lower:
        return None  # No fixed date for rolling
    elif 'spring' in plan_lower:
        return "2025-10-01"  # Fall deadline for spring admission
    elif 'summer' in plan_lower:
        return "2026-03-01"
    else:
        # Default to RD date
        return "2026-01-15"

def update_deadlines_in_file(filepath: str) -> bool:
    """Update application deadlines in a single JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find application_deadlines in the profile
        app_process = data.get('application_process', {})
        deadlines = app_process.get('application_deadlines', [])
        
        if not deadlines:
            # Try alternate path
            deadlines = data.get('application_deadlines', [])
            if deadlines:
                is_top_level = True
            else:
                return False  # No deadlines to update
        else:
            is_top_level = False
        
        # Update each deadline
        updated = False
        for deadline in deadlines:
            plan_type = deadline.get('plan_type', '')
            current_date = deadline.get('date', '')
            
            # Skip if no plan type
            if not plan_type:
                continue
            
            # Get new date
            new_date = get_updated_date(plan_type)
            
            if new_date and current_date != new_date:
                deadline['date'] = new_date
                updated = True
        
        if updated:
            # Write back to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        
        return False
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Update all university JSON files."""
    pattern = os.path.join(RESEARCH_DIR, "*.json")
    files = glob.glob(pattern)
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    print(f"Processing {len(files)} files...")
    
    for filepath in sorted(files):
        filename = os.path.basename(filepath)
        result = update_deadlines_in_file(filepath)
        
        if result:
            print(f"✓ Updated: {filename}")
            updated_count += 1
        elif result is False:
            skipped_count += 1
        else:
            error_count += 1
    
    print(f"\n=== Summary ===")
    print(f"Updated: {updated_count}")
    print(f"Skipped (no deadlines or already correct): {skipped_count}")
    print(f"Errors: {error_count}")

if __name__ == "__main__":
    main()
