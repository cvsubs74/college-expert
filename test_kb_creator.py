"""
Test script for Knowledge Base Creator Agent

Usage:
    python test_kb_creator.py "Stanford University"
    python test_kb_creator.py "UC Berkeley"
"""

import sys
import json
from datetime import datetime
from agents.sub_agents.knowledge_base_creator.agent import KnowledgeBaseCreator

def create_university_knowledge_base(university_name: str):
    """
    Create a comprehensive knowledge base for a university.
    
    Args:
        university_name: Name of the university to research
    
    Returns:
        dict: Complete university knowledge base
    """
    print(f"\n{'='*80}")
    print(f"Creating Knowledge Base for: {university_name}")
    print(f"{'='*80}\n")
    
    print("🔍 Starting parallel research agents...")
    print("   - Identity & Profile Researcher")
    print("   - Admissions Data Researcher")
    print("   - Academics & Majors Researcher")
    print("   - Financials Researcher")
    print("   - Student Life & Outcomes Researcher")
    print()
    
    # Run the knowledge base creator
    result = KnowledgeBaseCreator.run(
        user_prompt=f"Research and create a comprehensive knowledge base for {university_name}. "
                   f"Include all aspects: identity, admissions, academics, financials, and student life."
    )
    
    print("\n✅ Research complete!")
    print(f"\n{'='*80}")
    print("KNOWLEDGE BASE SUMMARY")
    print(f"{'='*80}\n")
    
    # Extract the knowledge base from result
    kb = result.get("university_knowledge_base", {})
    
    # Print summary
    print(f"University: {kb.get('university_name', 'N/A')}")
    print(f"Research Date: {kb.get('research_date', 'N/A')}")
    print(f"\nData Sources: {len(kb.get('data_sources', []))} sources")
    print(f"\n{kb.get('summary', 'No summary available')}")
    
    # Save to JSON file
    filename = f"kb_{university_name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(kb, f, indent=2)
    
    print(f"\n💾 Full knowledge base saved to: {filename}")
    print(f"\n{'='*80}\n")
    
    return kb

def main():
    if len(sys.argv) < 2:
        print("Usage: python test_kb_creator.py \"University Name\"")
        print("\nExamples:")
        print("  python test_kb_creator.py \"Stanford University\"")
        print("  python test_kb_creator.py \"UC Berkeley\"")
        print("  python test_kb_creator.py \"MIT\"")
        sys.exit(1)
    
    university_name = sys.argv[1]
    
    try:
        kb = create_university_knowledge_base(university_name)
        
        # Print key statistics
        print("\n📊 KEY STATISTICS:")
        print(f"{'='*80}")
        
        admissions = kb.get('admissions', {})
        print(f"\n🎓 Admissions:")
        print(f"   Acceptance Rate: {admissions.get('acceptance_rate', 'N/A')}")
        print(f"   GPA Range: {admissions.get('gpa_range', 'N/A')}")
        print(f"   SAT Range: {admissions.get('sat_range', 'N/A')}")
        
        academics = kb.get('academics', {})
        print(f"\n📚 Academics:")
        print(f"   Colleges/Schools: {len(academics.get('colleges_schools', []))}")
        print(f"   Top Majors: {len(academics.get('top_10_majors', []))}")
        
        financials = kb.get('financials', {})
        print(f"\n💰 Financials:")
        print(f"   Total COA: {financials.get('total_coa', 'N/A')}")
        print(f"   Meets Full Need: {financials.get('meets_full_need', 'N/A')}")
        
        student_life = kb.get('student_life', {})
        print(f"\n🎯 Career Outcomes:")
        print(f"   Job Placement: {student_life.get('job_placement_rate', 'N/A')}")
        print(f"   Avg Salary: {student_life.get('average_starting_salary', 'N/A')}")
        print(f"   Top Employers: {len(student_life.get('top_employers', []))}")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
