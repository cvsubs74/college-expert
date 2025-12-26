#!/usr/bin/env python3
"""Batch 4: Essay prompts for remaining universities."""
import json
import requests
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

# Remaining universities - many use UC PIQs or have simple "Why Us" essays
KNOWN_PROMPTS = {
    # Colorado Boulder
    "university_of_colorado_boulder": [
        {
            "prompt": "What do you hope to study, and why, at CU Boulder? Or if you don't know quite yet, think about your studies so far, extracurricular/after-school activities, jobs, volunteering, future goals, or anything else that has shaped your interests.",
            "word_limit": "250 words",
            "type": "Why Major",
            "required": True
        }
    ],
    # UC Santa Barbara - UC PIQs
    "university_of_california_santa_barbara": [
        {
            "prompt": "Describe an example of your leadership experience in which you have positively influenced others, helped resolve disputes or contributed to group efforts over time.",
            "word_limit": "350 words",
            "type": "Leadership",
            "required": True
        },
        {
            "prompt": "Every person has a creative side, and it can be expressed in many ways: problem-solving, original and innovative thinking, and artistically, to name a few. Describe how you express your creative side.",
            "word_limit": "350 words",
            "type": "Creativity",
            "required": True
        },
        {
            "prompt": "What would you say is your greatest talent or skill? How have you developed and demonstrated that talent over time?",
            "word_limit": "350 words",
            "type": "Talent",
            "required": True
        },
        {
            "prompt": "Describe the most significant challenge you have faced and the steps you have taken to overcome this challenge. How has this challenge affected your academic achievement?",
            "word_limit": "350 words",
            "type": "Challenge",
            "required": True
        }
    ],
    # Temple
    "temple_university": [
        {
            "prompt": "Tell us about yourself beyond your academic record. This can include interests outside the classroom, extracurricular activities, work experiences, or anything that reveals more about who you are.",
            "word_limit": "250+ words",
            "type": "Personal",
            "required": False
        }
    ],
    # Iowa State
    "iowa_state_university": [
        {
            "prompt": "Describe the academic, extracurricular, and/or personal experiences that have influenced your choice of major or area of study.",
            "word_limit": "250 words",
            "type": "Major",
            "required": False
        }
    ],
    # DePaul
    "depaul_university": [
        {
            "prompt": "DePaul University is the nation's largest Catholic university, guided by the Vincentian mission of access and service to all. How does this mission resonate with you?",
            "word_limit": "250 words",
            "type": "Values",
            "required": False
        }
    ],
    # Creighton
    "creighton_university": [
        {
            "prompt": "Creighton is a Jesuit university committed to developing men and women for others. Describe a time when you put the needs of others before your own and what you learned from that experience.",
            "word_limit": "300 words",
            "type": "Service",
            "required": True
        }
    ],
    # Seton Hall
    "seton_hall_university": [
        {
            "prompt": "What about Seton Hall University appeals to you, and how do you see yourself contributing to our community?",
            "word_limit": "250 words",
            "type": "Why Seton Hall",
            "required": False
        }
    ],
    # Elon
    "elon_university": [
        {
            "prompt": "Elon provides a dynamic learning environment characterized by engaged students and faculty. What aspects of Elon appeal to you, and how will you contribute to our community?",
            "word_limit": "250 words",
            "type": "Why Elon",
            "required": True
        }
    ],
    # Loyola Chicago
    "loyola_university_chicago": [
        {
            "prompt": "Loyola Chicago is committed to preparing people to lead extraordinary lives. What does 'living an extraordinary life' mean to you?",
            "word_limit": "300 words",
            "type": "Values",
            "required": True
        }
    ],
    # Seattle University
    "seattle_university": [
        {
            "prompt": "Seattle University's Jesuit mission emphasizes developing the whole person. How have you grown intellectually, personally, and spiritually in high school?",
            "word_limit": "300 words",
            "type": "Personal Growth",
            "required": True
        }
    ],
    # Ohio University
    "ohio_university": [
        {
            "prompt": "Tell us why you are interested in attending Ohio University and what aspects of our community appeal to you.",
            "word_limit": "250 words",
            "type": "Why Ohio",
            "required": False
        }
    ],
    # Kansas State
    "kansas_state_university": [
        {
            "prompt": "Tell us about your background, experiences, and goals. Why have you chosen your intended major?",
            "word_limit": "250 words",
            "type": "Major",
            "required": False
        }
    ],
    # Oklahoma State
    "oklahoma_state_university": [
        {
            "prompt": "Oklahoma State's brand promise is 'You Can Always Find a Cowboy Who Will.' Describe a time when you went above and beyond to help someone.",
            "word_limit": "250 words",
            "type": "Service",
            "required": False
        }
    ],
    # Colorado State
    "colorado_state_university": [
        {
            "prompt": "What about Colorado State University appeals to you, and how do you plan to contribute to our community?",
            "word_limit": "250 words",
            "type": "Why CSU",
            "required": False
        }
    ],
    # University of Arizona
    "university_of_arizona": [
        {
            "prompt": "Why have you chosen the University of Arizona, and what about our programs or community excites you?",
            "word_limit": "250 words",
            "type": "Why Arizona",
            "required": False
        }
    ],
    # University of Alabama
    "university_of_alabama": [
        {
            "prompt": "Why are you interested in attending the University of Alabama? How will you contribute to our community?",
            "word_limit": "300 words",
            "type": "Why Alabama",
            "required": False
        }
    ],
    # University of Arkansas
    "university_of_arkansas": [
        {
            "prompt": "Tell us why you want to attend the University of Arkansas and what makes you a good fit for our campus community.",
            "word_limit": "250 words",
            "type": "Why Arkansas",
            "required": False
        }
    ],
    # University of Cincinnati
    "university_of_cincinnati": [
        {
            "prompt": "Why are you interested in attending the University of Cincinnati? What excites you about your intended major or program?",
            "word_limit": "250 words",
            "type": "Why Major",
            "required": False
        }
    ],
    # University of Central Florida
    "university_of_central_florida": [
        {
            "prompt": "UCF is focused on developing the next generation of leaders and innovators. How will you use your education at UCF to make a positive impact?",
            "word_limit": "250 words",
            "type": "Goals",
            "required": False
        }
    ],
    # University at Buffalo
    "university_at_buffalo_suny": [
        {
            "prompt": "UB is New York's flagship public research university. What draws you to UB, and how will you take advantage of the opportunities here?",
            "word_limit": "250 words",
            "type": "Why UB",
            "required": False
        }
    ],
    # Stevens Institute
    "stevens_institute_of_technology": [
        {
            "prompt": "Stevens is known for developing problem-solvers and innovators. Describe a problem you've worked to solve and your approach.",
            "word_limit": "250 words",
            "type": "Problem Solving",
            "required": True
        }
    ],
    # Illinois Institute of Technology
    "illinois_institute_of_technology": [
        {
            "prompt": "Illinois Tech is committed to innovation and entrepreneurship. Tell us about a project or idea you've developed or would like to develop.",
            "word_limit": "250 words",
            "type": "Innovation",
            "required": False
        }
    ],
    # NJIT
    "new_jersey_institute_of_technology": [
        {
            "prompt": "NJIT prepares students to be leaders in a technology-driven world. How has technology influenced your life and academic interests?",
            "word_limit": "250 words",
            "type": "Technology",
            "required": False
        }
    ],
    # Missouri S&T
    "missouri_university_of_science_and_technology": [
        {
            "prompt": "Missouri S&T is focused on solving global challenges through STEM. What problem interests you most, and how might you address it?",
            "word_limit": "250 words",
            "type": "STEM",
            "required": False
        }
    ],
    # Clark University
    "clark_university": [
        {
            "prompt": "Clark's motto is 'Challenge Convention, Change Our World.' How do you plan to challenge convention in your education and career?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # Clarkson University
    "clarkson_university": [
        {
            "prompt": "Clarkson is committed to developing students who will be leaders and team players. Describe your approach to teamwork and collaboration.",
            "word_limit": "250 words",
            "type": "Teamwork",
            "required": False
        }
    ],
    # Adelphi University
    "adelphi_university": [
        {
            "prompt": "Adelphi is committed to transforming lives through education. How has your education so far transformed your perspective or goals?",
            "word_limit": "250 words",
            "type": "Personal Growth",
            "required": False
        }
    ],
    # Hofstra University
    "hofstra_university": [
        {
            "prompt": "Hofstra encourages students to find their pride. What are you most proud of, and how will you bring that passion to Hofstra?",
            "word_limit": "250 words",
            "type": "Pride",
            "required": False
        }
    ],
    # Duquesne University
    "duquesne_university": [
        {
            "prompt": "Duquesne's Spiritan mission emphasizes service to others and ethical leadership. How do these values align with your goals?",
            "word_limit": "300 words",
            "type": "Values",
            "required": True
        }
    ],
    # Saint Louis University
    "saint_louis_university": [
        {
            "prompt": "Saint Louis University's Jesuit mission is to pursue truth for the greater glory of God and for service of humanity. How does this mission resonate with you?",
            "word_limit": "300 words",
            "type": "Values",
            "required": True
        }
    ],
    # TCU
    "texas_christian_university": [
        {
            "prompt": "TCU is committed to educating ethical leaders who think freely and think globally. How will you embody these values as a Horned Frog?",
            "word_limit": "250 words",
            "type": "Leadership",
            "required": True
        }
    ],
    # San Diego State
    "san_diego_state_university": [
        {
            "prompt": "SDSU is committed to diversity, inclusion, and student success. How will you contribute to our diverse community?",
            "word_limit": "250 words",
            "type": "Community",
            "required": False
        }
    ],
    # Catholic University
    "the_catholic_university_of_america": [
        {
            "prompt": "The Catholic University of America's mission is the discovery and impartation of truth. How has your pursuit of truth shaped your academic journey?",
            "word_limit": "300 words",
            "type": "Values",
            "required": True
        }
    ],
    # Simmons University
    "simmons_university": [
        {
            "prompt": "Simmons empowers students to be leaders in their communities and careers. Describe how you plan to use your education to make a difference.",
            "word_limit": "250 words",
            "type": "Leadership",
            "required": True
        }
    ],
    # SUNY ESF
    "suny_college_of_environmental_science_and_forestry": [
        {
            "prompt": "SUNY-ESF is focused on environmental sustainability and science. What environmental issue concerns you most, and how might you address it?",
            "word_limit": "250 words",
            "type": "Environment",
            "required": True
        }
    ],
    # UC Merced
    "university_of_california_merced": [
        {
            "prompt": "Describe how you have taken advantage of a significant educational opportunity or worked to overcome an educational barrier you have faced.",
            "word_limit": "350 words",
            "type": "PIQ",
            "required": True
        },
        {
            "prompt": "What would you say is your greatest talent or skill? How have you developed and demonstrated that talent over time?",
            "word_limit": "350 words",
            "type": "PIQ",
            "required": True
        }
    ]
}


def update_and_ingest(filepath: Path, prompts: list) -> bool:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'application_process' not in data:
            data['application_process'] = {}
        data['application_process']['essay_prompts'] = prompts
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Ingest
        response = requests.post(KB_URL, json={"profile": data}, headers={"Content-Type": "application/json"}, timeout=300)
        return response.ok and response.json().get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    updated = ingested = 0
    not_found = []
    for university_id, prompts in KNOWN_PROMPTS.items():
        filepath = RESEARCH_DIR / f"{university_id}.json"
        if not filepath.exists():
            not_found.append(university_id)
            continue
        if update_and_ingest(filepath, prompts):
            print(f"✅ {university_id}: {len(prompts)} prompts added & ingested")
            updated += 1
            ingested += 1
        else:
            print(f"❌ {university_id}: failed")
    print(f"\n📊 Summary: Updated {updated}, Ingested {ingested}")
    if not_found:
        print(f"⚠️  Not found: {', '.join(not_found)}")


if __name__ == "__main__":
    main()
