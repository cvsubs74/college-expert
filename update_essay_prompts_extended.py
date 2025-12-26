#!/usr/bin/env python3
"""
Batch update university JSONs with real essay prompts - Extended Version.
"""
import json
import requests
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

# Extended known essay prompts for universities (2024-2025)
KNOWN_PROMPTS = {
    # Georgetown
    "georgetown_university": [
        {
            "prompt": "Briefly discuss the significance to you of the school or summer activity in which you have been most involved.",
            "word_limit": "Half page",
            "type": "Activity",
            "required": True
        },
        {
            "prompt": "As Georgetown is a diverse community, the Admissions Committee would like to know more about you in your own words. Please submit a brief personal or creative essay which you feel best describes you.",
            "word_limit": "One page",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "Describe your interest in studying at the College of Arts & Sciences, School of Nursing, School of Health, McDonough School of Business, or Walsh School of Foreign Service.",
            "word_limit": "One page",
            "type": "Why Georgetown",
            "required": True
        }
    ],
    # Vanderbilt
    "vanderbilt_university": [
        {
            "prompt": "Vanderbilt University's motto, Crescere aude, is Latin for 'dare to grow.' Reflect on how one or more aspects of your identity, culture, or background has played a role in your personal growth, and how it will contribute to our campus community.",
            "word_limit": "250 words",
            "type": "Identity",
            "required": True
        }
    ],
    # Notre Dame
    "university_of_notre_dame": [
        {
            "prompt": "Everyone has different priorities when considering their higher education options. Tell us about your 'non-negotiable' factor(s) when searching for your future college home.",
            "word_limit": "150 words",
            "type": "Why Notre Dame",
            "required": True
        },
        {
            "prompt": "How does faith influence the decisions you make?",
            "word_limit": "50-100 words",
            "type": "Values",
            "required": False
        },
        {
            "prompt": "Notre Dame's undergraduate experience is characterized by a collective sense of care for every person. How do you foster service to others in your community?",
            "word_limit": "50-100 words",
            "type": "Community",
            "required": False
        },
        {
            "prompt": "What would you fight for?",
            "word_limit": "50-100 words",
            "type": "Values",
            "required": False
        }
    ],
    # Rice
    "rice_university": [
        {
            "prompt": "Please explain why you wish to study in the academic areas you selected.",
            "word_limit": "150 words",
            "type": "Academic",
            "required": True
        },
        {
            "prompt": "Based upon your exploration of Rice University, what elements of the Rice experience appeal to you?",
            "word_limit": "150 words",
            "type": "Why Rice",
            "required": True
        },
        {
            "prompt": "The Residential College System is at the heart of Rice student life. What life experiences and/or unique perspectives are you looking forward to sharing with fellow Owls?",
            "word_limit": "500 words",
            "type": "Community",
            "required": True
        }
    ],
    # Johns Hopkins
    "johns_hopkins_university": [
        {
            "prompt": "Tell us about an important first in your life—big or small—that has shaped you.",
            "word_limit": "350 words",
            "type": "Personal",
            "required": True
        }
    ],
    # NYU
    "new_york_university": [
        {
            "prompt": "We are looking for students who embody the qualities of bridge builders. How have your experiences prepared you to build bridges and foster understanding in a global academic community?",
            "word_limit": "250 words",
            "type": "Community",
            "required": False
        }
    ],
    # Emory
    "emory_university": [
        {
            "prompt": "What academic areas are you interested in exploring at Emory University and why?",
            "word_limit": "200 words",
            "type": "Academic",
            "required": True
        },
        {
            "prompt": "Tell us about a community you have been part of where your participation helped to change or shape the community for the better.",
            "word_limit": "150 words",
            "type": "Community",
            "required": True
        }
    ],
    # UMich
    "university_of_michigan_ann_arbor": [
        {
            "prompt": "At the University of Michigan, we are focused on developing leaders and citizens who will challenge the present and enrich the future. Share how you are prepared to contribute to these goals.",
            "word_limit": "100-300 words",
            "type": "Leadership",
            "required": True
        },
        {
            "prompt": "Describe the unique qualities that attract you to the specific undergraduate College or School to which you are applying. How would that curriculum support your interests?",
            "word_limit": "100-550 words",
            "type": "Why Major",
            "required": True
        }
    ],
    # Tufts
    "tufts_university": [
        {
            "prompt": "It's cool to love learning. What excites your intellectual curiosity and why?",
            "word_limit": "200-250 words",
            "type": "Intellectual",
            "required": True
        },
        {
            "prompt": "How have the environments or experiences of your upbringing influenced the person you are today?",
            "word_limit": "200-250 words",
            "type": "Background",
            "required": True
        }
    ],
    # Boston College
    "boston_college": [
        {
            "prompt": "Each year at University Convocation, the incoming class participates in the 'Burning of the Boat.' What do you need to leave behind to embrace your future?",
            "word_limit": "400 words",
            "type": "Personal Growth",
            "required": True
        }
    ],
    # Boston University
    "boston_university": [
        {
            "prompt": "What about being a student at Boston University excites you?",
            "word_limit": "250 words",
            "type": "Why BU",
            "required": True
        }
    ],
    # WashU
    "washington_university_in_st_louis": [
        {
            "prompt": "Tell us about something that really sparks your intellectual curiosity and why.",
            "word_limit": "200 words",
            "type": "Intellectual",
            "required": True
        }
    ],
    # Purdue
    "purdue_university": [
        {
            "prompt": "How will opportunities at Purdue support your interests, both in and out of the classroom?",
            "word_limit": "250 words",
            "type": "Why Purdue",
            "required": True
        }
    ],
    # Virginia Tech
    "virginia_tech": [
        {
            "prompt": "Virginia Tech's motto is 'Ut Prosim' (That I May Serve). Share a time when you have contributed to a community.",
            "word_limit": "120 words",
            "type": "Community",
            "required": True
        }
    ],
    # Georgia Tech
    "georgia_institute_of_technology": [
        {
            "prompt": "Why do you want to study your chosen major at Georgia Tech, and what opportunities at GT will prepare you in that field after graduation?",
            "word_limit": "300 words",
            "type": "Why Major",
            "required": True
        }
    ],
    # UCLA
    "university_of_california_los_angeles": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
            "word_limit": "350 words",
            "type": "PIQ 1",
            "required": True
        },
        {
            "prompt": "Every person has a creative side. Describe how you express your creative side.",
            "word_limit": "350 words",
            "type": "PIQ 2",
            "required": True
        },
        {
            "prompt": "What would you say is your greatest talent or skill? How have you developed and demonstrated that talent over time?",
            "word_limit": "350 words",
            "type": "PIQ 3",
            "required": True
        },
        {
            "prompt": "Describe how you have made a significant impact on a community that is important to you.",
            "word_limit": "350 words",
            "type": "PIQ 4",
            "required": True
        }
    ],
    # UC San Diego
    "university_of_california_san_diego": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
            "word_limit": "350 words",
            "type": "PIQ 1",
            "required": True
        },
        {
            "prompt": "Every person has a creative side. Describe how you express your creative side.",
            "word_limit": "350 words",
            "type": "PIQ 2",
            "required": True
        }
    ],
    # UC Davis
    "university_of_california_davis": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
            "word_limit": "350 words",
            "type": "PIQ 1",
            "required": True
        },
        {
            "prompt": "What is the most significant challenge that society faces today?",
            "word_limit": "350 words",
            "type": "PIQ 2",
            "required": True
        }
    ],
    # UC Irvine
    "university_of_california_irvine": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity.",
            "word_limit": "350 words",
            "type": "PIQ",
            "required": True
        }
    ],
    # UIUC
    "university_of_illinois_urbana_champaign": [
        {
            "prompt": "Explain your interest in the major you selected and describe how you have recently explored or developed this interest inside and/or outside the classroom.",
            "word_limit": "150 words",
            "type": "Major",
            "required": True
        }
    ],
    # UW Madison
    "university_of_wisconsin_madison": [
        {
            "prompt": "Tell us why you would like to attend the University of Wisconsin-Madison. In addition, share with us the academic, extracurricular, or research opportunities you would take advantage of as a student.",
            "word_limit": "650 words",
            "type": "Why Wisconsin",
            "required": True
        }
    ],
    # Texas Austin
    "university_of_texas_at_austin": [
        {
            "prompt": "Why are you interested in the major you indicated as your first-choice major?",
            "word_limit": "250-300 words",
            "type": "Major",
            "required": True
        },
        {
            "prompt": "Describe how your experiences, perspectives, talents, and/or your involvement in leadership activities will help you to make an impact at UT Austin and beyond.",
            "word_limit": "500 words",
            "type": "Leadership",
            "required": True
        }
    ],
    # UVA
    "university_of_virginia": [
        {
            "prompt": "What's your favorite word and why?",
            "word_limit": "50 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "We are a community with quirks, both in language and in traditions. Describe one of your quirks and why it is part of who you are.",
            "word_limit": "100 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "UVA students paint messages on Beta Bridge when they want to share news with the community. What would you paint on Beta Bridge and why?",
            "word_limit": "50 words",
            "type": "Community",
            "required": True
        }
    ],
    # UNC
    "university_of_north_carolina_at_chapel_hill": [
        {
            "prompt": "Describe an aspect of your identity (example: your religion, culture, race, sexual or gender identity, affinity group, etc.). How has this aspect of your identity shaped your life experiences thus far?",
            "word_limit": "200-250 words",
            "type": "Identity",
            "required": True
        },
        {
            "prompt": "If you could change one thing to better your community, what would it be and why?",
            "word_limit": "200-250 words",
            "type": "Community",
            "required": True
        }
    ],
    # Wake Forest
    "wake_forest_university": [
        {
            "prompt": "Tell us what piques your intellectual curiosity or fuels your passions. This can include books, music, podcasts, movies, works of art, blogs, or anything else that deepen your interests.",
            "word_limit": "150 words",
            "type": "Intellectual",
            "required": True
        },
        {
            "prompt": "What are you good at? What would you like to improve at?",
            "word_limit": "150 words",
            "type": "Personal",
            "required": True
        }
    ],
    # Villanova
    "villanova_university": [
        {
            "prompt": "St. Augustine believed in the essential connection between the mind and the heart. For him, our intellect shapes and forms our character, helping us not only to think clearly and critically, but also to live with purpose, care, and passion. What is a question that is meaningful to your life, and of which you continue to seek an answer?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # Northeastern
    "northeastern_university": [
        {
            "prompt": "Northeastern's Global Experience is built on three pillars: global mindset, global awareness, and global engagement. How would you take advantage of opportunities at Northeastern to develop your own global experience?",
            "word_limit": "250 words",
            "type": "Why Northeastern",
            "required": True
        }
    ],
    # Case Western
    "case_western_reserve_university": [
        {
            "prompt": "Think about a device, object, or machine you find fascinating. What do you think is interesting about the way it was designed or functions?",
            "word_limit": "200 words",
            "type": "Intellectual",
            "required": False
        }
    ],
    # Lehigh
    "lehigh_university": [
        {
            "prompt": "Lehigh students are passionate about ideas, making change, and having impact. How do you hope to make your mark at Lehigh, and what impact do you hope to have on campus?",
            "word_limit": "200 words",
            "type": "Why Lehigh",
            "required": True
        }
    ],
    # Tulane
    "tulane_university": [
        {
            "prompt": "Please describe why you are interested in attending Tulane. We want to get to know you better. Consider sharing something that illustrates what Tulane can offer you and what you can contribute.",
            "word_limit": "200 words",
            "type": "Why Tulane",
            "required": True
        }
    ],
    # SMU
    "southern_methodist_university": [
        {
            "prompt": "SMU appeals to students for a variety of reasons. Briefly describe why you are interested in attending SMU and what specific aspects of the university are particularly attractive.",
            "word_limit": "250 words",
            "type": "Why SMU",
            "required": True
        }
    ],
    # Pepperdine
    "pepperdine_university": [
        {
            "prompt": "Pepperdine is a Christian university where students can grow spiritually and are encouraged to consider their place in the world. Tell us about how you would contribute to this environment.",
            "word_limit": "50 words",
            "type": "Values",
            "required": True
        }
    ]
}


def update_university_prompts(filepath: Path, prompts: list) -> bool:
    """Update a university JSON file with essay prompts."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if 'application_process' not in data:
            data['application_process'] = {}
        
        data['application_process']['essay_prompts'] = prompts
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        print(f"Error updating {filepath}: {e}")
        return False


def ingest_university(filepath: Path) -> bool:
    """Ingest university to knowledge base."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        
        response = requests.post(
            KB_URL,
            json={"profile": profile},
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        if response.ok:
            result = response.json()
            return result.get('success', False)
        return False
    except Exception as e:
        print(f"Error ingesting {filepath}: {e}")
        return False


def main():
    updated = 0
    ingested = 0
    not_found = []
    
    for university_id, prompts in KNOWN_PROMPTS.items():
        filepath = RESEARCH_DIR / f"{university_id}.json"
        
        if not filepath.exists():
            not_found.append(university_id)
            continue
        
        if update_university_prompts(filepath, prompts):
            print(f"✏️  {university_id}: updated with {len(prompts)} prompts")
            updated += 1
            
            if ingest_university(filepath):
                print(f"✅ {university_id}: ingested")
                ingested += 1
            else:
                print(f"❌ {university_id}: ingest failed")
        else:
            print(f"❌ {university_id}: update failed")
    
    print(f"\n📊 Summary: Updated {updated}, Ingested {ingested}")
    if not_found:
        print(f"⚠️  Not found: {', '.join(not_found)}")


if __name__ == "__main__":
    main()
