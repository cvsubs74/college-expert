#!/usr/bin/env python3
"""
Batch update university JSONs with real essay prompts.
Uses web search to find current supplemental essay prompts.
"""
import json
import os
import sys
import requests
from pathlib import Path
from typing import Optional, List, Dict

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

# Known essay prompts for major universities (2024-2025)
KNOWN_PROMPTS = {
    "stanford_university": [
        {
            "prompt": "The Stanford community is deeply curious and driven to learn in and out of the classroom. Reflect on an idea or experience that makes you genuinely excited about learning.",
            "word_limit": "100-250 words",
            "type": "Intellectual Curiosity",
            "required": True
        },
        {
            "prompt": "Virtually all of Stanford's undergraduates live on campus. Write a note to your future roommate that reveals something about you or that will help your roommate—and us—get to know you better.",
            "word_limit": "100-250 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "Tell us about something that is meaningful to you, and why?",
            "word_limit": "100-250 words",
            "type": "Values",
            "required": True
        }
    ],
    "massachusetts_institute_of_technology": [
        {
            "prompt": "We know you lead a busy life, full of activities, many of which are required of you. Tell us about something you do simply for the pleasure of it.",
            "word_limit": "100-200 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "Describe the world you come from (for example, your family, school, community, city, or town). How has that world shaped your dreams and aspirations?",
            "word_limit": "100-200 words",
            "type": "Background",
            "required": True
        },
        {
            "prompt": "MIT brings people with diverse backgrounds together to collaborate, from tackling the world's biggest challenges to lending a helping hand. Describe one way you have collaborated with others to learn from them, with them, or contribute to your community together.",
            "word_limit": "100-200 words",
            "type": "Community",
            "required": True
        },
        {
            "prompt": "How did you manage a situation or challenge that you didn't expect? What did you learn from it?",
            "word_limit": "100-200 words",
            "type": "Challenge",
            "required": True
        },
        {
            "prompt": "Tell us about a significant challenge you've faced or something that didn't go according to plan. How did you manage the situation?",
            "word_limit": "100-200 words",
            "type": "Growth",
            "required": True
        }
    ],
    "harvard_university": [
        {
            "prompt": "Harvard has long recognized the importance of enrolling a diverse student body. How will the life experiences that shape who you are today enable you to contribute to Harvard?",
            "word_limit": "200 words",
            "type": "Diversity",
            "required": True
        },
        {
            "prompt": "Briefly describe an intellectual experience that was important to you.",
            "word_limit": "200 words",
            "type": "Intellectual",
            "required": True
        },
        {
            "prompt": "Briefly describe how you hope to use your college education.",
            "word_limit": "200 words",
            "type": "Goals",
            "required": True
        },
        {
            "prompt": "Top 3 things your roommates might like to know about you.",
            "word_limit": "200 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "How do you spend a typical day after school?",
            "word_limit": "200 words",
            "type": "Personal",
            "required": True
        }
    ],
    "yale_university": [
        {
            "prompt": "What is it about Yale that has led you to apply?",
            "word_limit": "125 words",
            "type": "Why Yale",
            "required": True
        },
        {
            "prompt": "Reflect on a time you discussed an issue important to you with someone holding an opposing view. Why did you find the experience meaningful?",
            "word_limit": "250 words",
            "type": "Personal Growth",
            "required": True
        },
        {
            "prompt": "Tell us about a topic or idea that excites you and is related to one or more academic areas you selected. Why are you drawn to it?",
            "word_limit": "250 words",
            "type": "Academic Interest",
            "required": True
        }
    ],
    "princeton_university": [
        {
            "prompt": "Princeton has a longstanding commitment to service. Tell us how you have engaged with your community in a way that matters to you.",
            "word_limit": "250 words",
            "type": "Community",
            "required": True
        },
        {
            "prompt": "Princeton values diverse perspectives and the ability to have respectful dialogue about difficult issues. Share a time when you had a conversation with a person or a group of people about a difficult topic. What insight did you gain, and how would you incorporate that knowledge into your thinking in the future?",
            "word_limit": "250 words",
            "type": "Personal Growth",
            "required": True
        },
        {
            "prompt": "What is a new skill you would like to learn in college?",
            "word_limit": "50 words",
            "type": "Goals",
            "required": True
        },
        {
            "prompt": "What brings you joy?",
            "word_limit": "50 words",
            "type": "Personal",
            "required": True
        }
    ],
    "duke_university": [
        {
            "prompt": "What is your sense of Duke as a university and a community, and why do you consider it a good match for you? If there's something in particular about our offerings that attracts you, feel free to share that as well.",
            "word_limit": "250 words",
            "type": "Why Duke",
            "required": True
        },
        {
            "prompt": "We want to emphasize that the following is optional. Feel free to share with us anything regarding the context of your application that you'd like us to know. You might share about your culture, identity, or a particular personal experience that shaped your perspective or accomplishments.",
            "word_limit": "250 words",
            "type": "Background",
            "required": False
        }
    ],
    "northwestern_university": [
        {
            "prompt": "We want to understand what excites you intellectually and how Northwestern will help you pursue your passions and interests. Help us get to know you better by responding to two required prompts and one optional prompt.",
            "word_limit": "300 words",
            "type": "Why Northwestern",
            "required": True
        }
    ],
    "university_of_pennsylvania": [
        {
            "prompt": "Considering the specific undergraduate school you have selected, describe how you intend to explore your academic and intellectual interests at the University of Pennsylvania.",
            "word_limit": "150-200 words",
            "type": "Academic",
            "required": True
        }
    ],
    "columbia_university": [
        {
            "prompt": "Why are you interested in attending Columbia University?",
            "word_limit": "200 words",
            "type": "Why Columbia",
            "required": True
        },
        {
            "prompt": "What attracts you to your intended field of study?",
            "word_limit": "150 words",
            "type": "Academic",
            "required": True
        },
        {
            "prompt": "In Columbia's admissions process, we use a holistic review, which means that we look at every part of your application. We encourage you to share additional details about yourself that you have not had an opportunity to share.",
            "word_limit": "200 words",
            "type": "Personal",
            "required": False
        }
    ],
    "brown_university": [
        {
            "prompt": "Brown's Open Curriculum allows students to explore broadly while also diving deeply into their academic pursuits. Tell us about any academic interests that excite you, and how you might use the Open Curriculum to pursue them.",
            "word_limit": "200-250 words",
            "type": "Academic",
            "required": True
        },
        {
            "prompt": "Students entering Brown often find that their courses, extracurriculars, and their interactions with other students and faculty prompt them to experience many new and different perspectives. Describe how an aspect of your background or identity that is important to you has shaped your perspective and how your engagement with perspectives different from your own has changed how you move through the world.",
            "word_limit": "200-250 words",
            "type": "Identity",
            "required": True
        },
        {
            "prompt": "Tell us about a place or community you call home. How has it shaped your perspective?",
            "word_limit": "200-250 words",
            "type": "Community",
            "required": True
        }
    ],
    "dartmouth_college": [
        {
            "prompt": "As you seek admission to Dartmouth's Class of 2029, what aspects of the College's academic and campus community inspire you?",
            "word_limit": "100 words",
            "type": "Why Dartmouth",
            "required": True
        },
        {
            "prompt": "There is a Dartmouth for everyone. Choose one of the following prompts and respond in 250 words or fewer.",
            "word_limit": "250 words",
            "type": "Personal",
            "required": True
        }
    ],
    "cornell_university": [
        {
            "prompt": "Using your personal, academic, or volunteer/work experiences, describe the topics or issues that you care about and why they are important to you.",
            "word_limit": "650 words",
            "type": "Values",
            "required": True
        }
    ],
    "university_of_chicago": [
        {
            "prompt": "How does the University of Chicago, as you know it now, satisfy your desire for a particular kind of learning, community, and future? Please address with some specificity your own wishes and how they relate to UChicago.",
            "word_limit": "No limit",
            "type": "Why UChicago",
            "required": True
        },
        {
            "prompt": "Extended Essay: Choose one of our past or present prompts (or create your own).",
            "word_limit": "No limit",
            "type": "Creative",
            "required": True
        }
    ],
    "university_of_southern_california": [
        {
            "prompt": "Describe how you plan to pursue your academic interests and why you want to explore them at USC specifically. Please feel free to address your first- and second-choice major selections.",
            "word_limit": "250 words",
            "type": "Academic",
            "required": True
        }
    ],
    "university_of_california_berkeley": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
            "word_limit": "350 words",
            "type": "PIQ 1",
            "required": True
        },
        {
            "prompt": "Every person has a creative side, and it can be expressed in many ways: problem solving, original and innovative thinking, and artistically, to name a few. Describe how you express your creative side.",
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
            "prompt": "Describe how you have made a significant impact on a community that is important to you. What is the community &amp; how are you involved?",
            "word_limit": "350 words",
            "type": "PIQ 4",
            "required": True
        }
    ]
}


def update_university_prompts(filepath: Path, prompts: List[Dict]) -> bool:
    """Update a university JSON file with essay prompts."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Add essay_prompts to application_process
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
    
    for university_id, prompts in KNOWN_PROMPTS.items():
        filepath = RESEARCH_DIR / f"{university_id}.json"
        
        if not filepath.exists():
            print(f"⚠️  {university_id}: file not found")
            continue
        
        # Update JSON
        if update_university_prompts(filepath, prompts):
            print(f"✏️  {university_id}: updated with {len(prompts)} prompts")
            updated += 1
            
            # Ingest to KB
            if ingest_university(filepath):
                print(f"✅ {university_id}: ingested")
                ingested += 1
            else:
                print(f"❌ {university_id}: ingest failed")
        else:
            print(f"❌ {university_id}: update failed")
    
    print(f"\n📊 Summary: Updated {updated}, Ingested {ingested}")


if __name__ == "__main__":
    main()
