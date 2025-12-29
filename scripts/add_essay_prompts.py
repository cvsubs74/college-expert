#!/usr/bin/env python3
"""
Script to add missing essay prompts to university research JSON files.
Prompts are for the 2025-2026 admissions cycle (with 2024-2025 fallback).
"""
import json
import os
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")

# UC Personal Insight Questions (2025-2026) - Choose 4 of 8, 350 words each
UC_PIQ_ESSAY_PROMPTS = [
    {
        "prompt": "Describe an example of your leadership experience in which you have positively influenced others, helped resolve disputes or contributed to group efforts over time.",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "Every person has a creative side, and it can be expressed in many ways: problem solving, original and innovative thinking, and artistically, to name a few. Describe how you express your creative side.",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "What would you say is your greatest talent or skill? How have you developed and demonstrated that talent over time?",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "Describe the most significant challenge you have faced and the steps you have taken to overcome this challenge. How has this challenge affected your academic achievement?",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "Think about an academic subject that inspires you. Describe how you have furthered this interest inside and/or outside of the classroom.",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "What have you done to make your school or your community a better place?",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    },
    {
        "prompt": "Beyond what has already been shared in your application, what do you believe makes you a strong candidate for admissions to the University of California?",
        "word_limit": 350,
        "required": False,
        "note": "Choose 4 of 8 PIQs",
        "application_cycle": "2025-2026"
    }
]

# University-specific essay prompts (2025-2026)
ESSAY_PROMPTS = {
    # Washington University in St. Louis (2025-2026)
    "washington_university_in_st_louis": [
        {
            "prompt": "Please tell us what you are interested in studying at college and why. Undecided about your academic interest(s)? Don't worry—tell us what excites you about the academic division you selected. Remember that all of our first-year students enter officially 'undeclared' and work closely with their team of academic advisors to discover their academic passions.",
            "word_limit": 200,
            "required": True,
            "note": "Required supplemental essay",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "WashU supports engagement in the St. Louis community by considering the university as 'In St. Louis, For St. Louis.' What is a community you are a part of and your place or impact within it?",
            "word_limit": 250,
            "required": False,
            "note": "Optional - choose one of two options",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "WashU strives to know every undergraduate student 'By Name & Story.' How have your life experiences shaped your story?",
            "word_limit": 250,
            "required": False,
            "note": "Optional - choose one of two options",
            "application_cycle": "2025-2026"
        }
    ],
    
    # Texas A&M University (2025-2026)
    "texas_a_m_university": [
        {
            "prompt": "Tell us your story. What unique opportunities or challenges have you experienced throughout your high school career that have shaped who you are today?",
            "word_limit": 750,
            "required": True,
            "note": "ApplyTexas Essay A - Personal Statement",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "Describe a life event which you feel has prepared you to be successful in college.",
            "word_limit": 250,
            "required": True,
            "note": "Short Answer 1",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "Tell us about the person who has most impacted your life and why.",
            "word_limit": 250,
            "required": True,
            "note": "Short Answer 2",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "If there are additional personal challenges, hardships, or opportunities (including COVID-related experiences) that have shaped or impacted your abilities or academic credentials, which you have not already written about, please note them in the space below.",
            "word_limit": 500,
            "required": False,
            "note": "Optional additional information",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Central Florida (2025-2026)
    "university_of_central_florida": [
        {
            "prompt": "Why did you choose to apply to UCF?",
            "word_limit": 250,
            "required": False,
            "note": "Optional essay - strongly encouraged",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "What qualities or unique characteristics do you possess that will allow you to contribute to the UCF community?",
            "word_limit": 250,
            "required": False,
            "note": "Optional essay - strongly encouraged",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "Please briefly elaborate on one of your extracurricular activities or work experiences.",
            "word_limit": 250,
            "required": False,
            "note": "Optional essay - strongly encouraged",
            "application_cycle": "2025-2026"
        }
    ],
    
    # Colorado School of Mines (2025-2026)
    "colorado_school_of_mines": [
        {
            "prompt": "What element on the periodic table best represents you and why?",
            "word_limit": 250,
            "required": False,
            "note": "Optional but strongly recommended",
            "application_cycle": "2025-2026"
        },
        {
            "prompt": "Why do you want to be an Oredigger? You can share what you want to study, your future involvement and activities, or anything else about the Mines experience that excites you.",
            "word_limit": 250,
            "required": False,
            "note": "Optional but strongly recommended",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Hawaii at Manoa
    "university_of_hawaii_at_manoa": [
        {
            "prompt": "Please describe any special circumstances or qualifications which you feel should be considered in the review of your admission credentials.",
            "word_limit": 500,
            "required": False,
            "note": "Optional personal statement",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Missouri
    "university_of_missouri": [
        {
            "prompt": "Tell us about your background, interests, and what influenced your decision to apply to Mizzou. We'd like to learn more about you!",
            "word_limit": 500,
            "required": False,
            "note": "Optional essay",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Arkansas
    "university_of_arkansas": [
        {
            "prompt": "Tell us about something you are passionate about and why. How has this passion shaped who you are today?",
            "word_limit": 650,
            "required": False,
            "note": "Optional essay",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Oklahoma
    "university_of_oklahoma": [
        {
            "prompt": "The University of Oklahoma values a diverse community of students with different backgrounds, perspectives, and experiences. What unique contributions might you make to OU?",
            "word_limit": 500,
            "required": False,
            "note": "Optional supplemental essay",
            "application_cycle": "2025-2026"
        }
    ],
    
    # University of Rhode Island
    "university_of_rhode_island": [
        {
            "prompt": "Please share anything you would like us to know about yourself that perhaps was not evident in other parts of this application.",
            "word_limit": 500,
            "required": False,
            "note": "Optional personal statement",
            "application_cycle": "2025-2026"
        }
    ],
    
    # Ohio University
    "ohio_university": [
        {
            "prompt": "At Ohio University, we value the unique experiences and perspectives that each student brings to our community. Please share something about yourself that you believe would contribute to or benefit from the OHIO community.",
            "word_limit": 500,
            "required": False,
            "note": "Optional essay",
            "application_cycle": "2025-2026"
        }
    ],
    
    # Clark University
    "clark_university": [
        {
            "prompt": "Clark University invites students to 'Challenge Convention. Change Our World.' Describe a time when you challenged a conventional idea, norm, or practice.",
            "word_limit": 300,
            "required": False,
            "note": "Optional supplemental essay",
            "application_cycle": "2025-2026"
        }
    ],
    
    # UC Schools - All use PIQs
    "university_of_california_san_diego_0": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_san_diego_1": UC_PIQ_ESSAY_PROMPTS,
    "uc_san_diego": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_berkeley": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_los_angeles": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_davis": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_irvine": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_santa_barbara": UC_PIQ_ESSAY_PROMPTS,
    "university_of_california_merced": UC_PIQ_ESSAY_PROMPTS,
}


def update_university_essay_prompts(university_id: str, prompts: list) -> dict:
    """Update a university's JSON file with essay prompts."""
    file_path = RESEARCH_DIR / f"{university_id}.json"
    
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Find the right path to application_process
        if "university_profile" in data:
            profile = data["university_profile"]
        elif "profile" in data:
            profile = data["profile"]
        else:
            profile = data
        
        # Ensure application_process exists
        if "application_process" not in profile:
            profile["application_process"] = {}
        
        # Handle supplemental_requirements - may be list or dict
        existing_supp = profile["application_process"].get("supplemental_requirements")
        
        if isinstance(existing_supp, list):
            # Convert list to object structure, preserving existing data
            profile["application_process"]["supplemental_requirements"] = {
                "requirements_list": existing_supp,
                "essay_prompts": prompts
            }
        elif isinstance(existing_supp, dict):
            # Already an object, just add essay_prompts
            existing_supp["essay_prompts"] = prompts
        else:
            # Doesn't exist or is None
            profile["application_process"]["supplemental_requirements"] = {
                "essay_prompts": prompts
            }
        
        # Write back
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {"success": True, "university_id": university_id}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


def main():
    print("=" * 60)
    print("Adding Missing Essay Prompts (2025-2026)")
    print("=" * 60)
    
    updated = 0
    failed = 0
    
    for university_id, prompts in ESSAY_PROMPTS.items():
        print(f"\nUpdating {university_id}...")
        result = update_university_essay_prompts(university_id, prompts)
        
        if result.get("success"):
            print(f"  ✓ Added {len(prompts)} essay prompt(s)")
            updated += 1
        else:
            print(f"  ✗ Failed: {result.get('error')}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Summary:")
    print(f"  Updated: {updated}")
    print(f"  Failed: {failed}")
    print("=" * 60)


if __name__ == "__main__":
    main()
