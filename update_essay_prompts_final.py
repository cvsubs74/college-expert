#!/usr/bin/env python3
"""Final batch: Essay prompts for remaining universities."""
import json
import requests
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

KNOWN_PROMPTS = {
    # University of Florida
    "university_of_florida": [
        {
            "prompt": "What has shaped who you are today and the goals you're working toward? Tell us about your experiences, achievements, and future aspirations.",
            "word_limit": "250 words",
            "type": "Personal",
            "required": True
        }
    ],
    # University of Georgia
    "university_of_georgia": [
        {
            "prompt": "The University of Georgia's motto is 'To Teach, to Serve, and to Inquire into the Nature of Things.' How do these ideals resonate with you?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # University of Maryland
    "university_of_maryland_college_park": [
        {
            "prompt": "If I could travel anywhere, I would go to... (Complete this statement in about 650 words max, using the personal essay as an opportunity to tell us about yourself.)",
            "word_limit": "650 words",
            "type": "Personal",
            "required": False
        }
    ],
    # University of Miami
    "university_of_miami": [
        {
            "prompt": "The University of Miami is a vibrant and diverse academic community. What unique perspectives or experiences would you bring to our campus?",
            "word_limit": "250 words",
            "type": "Diversity",
            "required": True
        }
    ],
    # University of Minnesota
    "university_of_minnesota_twin_cities": [
        {
            "prompt": "Describe a moment when you pushed yourself beyond your comfort zone. What did you learn?",
            "word_limit": "150 words",
            "type": "Personal Growth",
            "required": False
        }
    ],
    # University of Pittsburgh
    "university_of_pittsburgh": [
        {
            "prompt": "Please describe a meaningful experience from your life and how it has helped shape who you are today.",
            "word_limit": "450 words",
            "type": "Personal",
            "required": True
        }
    ],
    # University of Rochester
    "university_of_rochester": [
        {
            "prompt": "The University of Rochester is home to a diverse community of students who share certain key qualities including intellectual curiosity, openness to different ideas, and a commitment to their interests. How would these traits help you thrive at Rochester?",
            "word_limit": "200 words",
            "type": "Why Rochester",
            "required": True
        }
    ],
    # University of Washington
    "university_of_washington": [
        {
            "prompt": "Our families and communities often define us and our individual worlds. Community might refer to your cultural group, extended family, religious group, neighborhood or school, sports team or club, co-workers, etc. Describe the world you come from and how you, as a product of it, might add to the diversity of the UW.",
            "word_limit": "300 words",
            "type": "Community",
            "required": True
        }
    ],
    # University of Connecticut
    "university_of_connecticut": [
        {
            "prompt": "Please tell us about how your lived experiences, perspectives, and/or identity have helped shape who you are today and how they will enrich UConn's community.",
            "word_limit": "200 words",
            "type": "Identity",
            "required": True
        }
    ],
    # University of Delaware
    "university_of_delaware": [
        {
            "prompt": "Why are you interested in the University of Delaware and your intended major? How will UD help you achieve your goals?",
            "word_limit": "250 words",
            "type": "Why Delaware",
            "required": True
        }
    ],
    # University of Denver
    "university_of_denver": [
        {
            "prompt": "DU's educational experience challenges students to be creative problem-solvers and active citizens. How will you contribute to this environment?",
            "word_limit": "250 words",
            "type": "Contribution",
            "required": True
        }
    ],
    # University of Iowa
    "university_of_iowa": [
        {
            "prompt": "Describe a time when you witnessed or experienced an injustice. How did it affect you, and what did you learn from the experience?",
            "word_limit": "250 words",
            "type": "Values",
            "required": False
        }
    ],
    # University of Kansas
    "university_of_kansas": [
        {
            "prompt": "KU is committed to developing leaders who will shape our world. How will your education at KU contribute to your goals?",
            "word_limit": "250 words",
            "type": "Goals",
            "required": False
        }
    ],
    # University of Kentucky
    "university_of_kentucky": [
        {
            "prompt": "UK is dedicated to improving people's lives. Tell us how you plan to make a positive impact through your career or community involvement.",
            "word_limit": "250 words",
            "type": "Impact",
            "required": False
        }
    ],
    # University of Louisville
    "university_of_louisville": [
        {
            "prompt": "What aspects of the University of Louisville appeal to you, and how do you see yourself contributing to our campus community?",
            "word_limit": "250 words",
            "type": "Why Louisville",
            "required": False
        }
    ],
    # UMass Amherst
    "university_of_massachusetts_amherst": [
        {
            "prompt": "Please describe a time when you contributed to a group effort. What was your role, and what did you learn from the experience?",
            "word_limit": "250 words",
            "type": "Teamwork",
            "required": True
        }
    ],
    # University of Missouri
    "university_of_missouri": [
        {
            "prompt": "Mizzou is committed to developing students who will lead and make a difference. How do you plan to contribute to our community?",
            "word_limit": "250 words",
            "type": "Community",
            "required": False
        }
    ],
    # University of Nebraska
    "university_of_nebraska_lincoln": [
        {
            "prompt": "What experiences have prepared you for the academic challenges and opportunities at the University of Nebraska-Lincoln?",
            "word_limit": "250 words",
            "type": "Academic",
            "required": False
        }
    ],
    # University of New Hampshire
    "university_of_new_hampshire": [
        {
            "prompt": "UNH is known for its commitment to sustainability and community engagement. How do these values align with your own?",
            "word_limit": "250 words",
            "type": "Values",
            "required": False
        }
    ],
    # University of Oklahoma
    "university_of_oklahoma": [
        {
            "prompt": "OU encourages students to be leaders and change-makers. How will you leverage your OU experience to make an impact?",
            "word_limit": "250 words",
            "type": "Leadership",
            "required": False
        }
    ],
    # University of Oregon
    "university_of_oregon": [
        {
            "prompt": "At the University of Oregon, we embrace the concept of 'Ducks in Service.' How have you demonstrated service to your community?",
            "word_limit": "250 words",
            "type": "Service",
            "required": False
        }
    ],
    # University of Rhode Island
    "university_of_rhode_island": [
        {
            "prompt": "URI is committed to helping students discover their potential. What do you hope to discover about yourself during your time at URI?",
            "word_limit": "250 words",
            "type": "Goals",
            "required": False
        }
    ],
    # University of San Diego
    "university_of_san_diego": [
        {
            "prompt": "USD's mission emphasizes developing ethical leaders for a more humane world. How does this mission resonate with your values?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # University of San Francisco
    "university_of_san_francisco": [
        {
            "prompt": "USF's Jesuit mission emphasizes changing the world from here. How do you plan to make a difference in your community?",
            "word_limit": "250 words",
            "type": "Impact",
            "required": True
        }
    ],
    # University of South Carolina
    "university_of_south_carolina": [
        {
            "prompt": "What about the University of South Carolina excites you, and how will you contribute to the Gamecock community?",
            "word_limit": "250 words",
            "type": "Why USC",
            "required": False
        }
    ],
    # University of South Florida
    "university_of_south_florida": [
        {
            "prompt": "USF is committed to student success and innovation. How will you take advantage of opportunities at USF to achieve your goals?",
            "word_limit": "250 words",
            "type": "Goals",
            "required": False
        }
    ],
    # University of Tennessee
    "university_of_tennessee_knoxville": [
        {
            "prompt": "UT is committed to developing leaders who will make a difference. Describe a time when you demonstrated leadership.",
            "word_limit": "250 words",
            "type": "Leadership",
            "required": False
        }
    ],
    # University of Vermont
    "university_of_vermont": [
        {
            "prompt": "UVM is committed to sustainability and environmental stewardship. How do these values align with your goals?",
            "word_limit": "250 words",
            "type": "Values",
            "required": False
        }
    ],
    # WPI
    "worcester_polytechnic_institute": [
        {
            "prompt": "WPI's project-based education prepares students to solve real-world problems. Describe a problem you're passionate about solving.",
            "word_limit": "250 words",
            "type": "Problem Solving",
            "required": True
        }
    ],
    # University of Dayton
    "university_of_dayton": [
        {
            "prompt": "UD is a Catholic, Marianist university committed to community and service. How do these values align with yours?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # University of Hawaii
    "university_of_hawaii_at_manoa": [
        {
            "prompt": "UH Manoa is unique in its location and cultural diversity. How will you contribute to our diverse community?",
            "word_limit": "250 words",
            "type": "Diversity",
            "required": False
        }
    ],
    # University of La Verne
    "university_of_la_verne": [
        {
            "prompt": "La Verne is committed to developing ethical leaders. How have your experiences prepared you for ethical leadership?",
            "word_limit": "250 words",
            "type": "Leadership",
            "required": True
        }
    ],
    # UMass Lowell
    "university_of_massachusetts_lowell": [
        {
            "prompt": "UMass Lowell is focused on experiential learning and real-world impact. How will you take advantage of these opportunities?",
            "word_limit": "250 words",
            "type": "Experience",
            "required": False
        }
    ],
    # University of the Pacific
    "university_of_the_pacific": [
        {
            "prompt": "Pacific's motto is 'Potential Realized.' What potential do you hope to realize during your time at Pacific?",
            "word_limit": "250 words",
            "type": "Goals",
            "required": True
        }
    ],
    # University of Tulsa
    "university_of_tulsa": [
        {
            "prompt": "TU is committed to developing students who make a difference. How do you plan to contribute to our community?",
            "word_limit": "250 words",
            "type": "Community",
            "required": True
        }
    ],
    # University of St. Thomas
    "university_of_st_thomas_minnesota": [
        {
            "prompt": "St. Thomas is grounded in Catholic intellectual tradition. How does this tradition resonate with your educational goals?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # Yeshiva University
    "yeshiva_university": [
        {
            "prompt": "Yeshiva University combines Jewish values with secular education. How will this unique blend support your growth?",
            "word_limit": "250 words",
            "type": "Values",
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
        response = requests.post(KB_URL, json={"profile": data}, headers={"Content-Type": "application/json"}, timeout=300)
        return response.ok and response.json().get('success', False)
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    updated = 0
    not_found = []
    for uid, prompts in KNOWN_PROMPTS.items():
        fp = RESEARCH_DIR / f"{uid}.json"
        if not fp.exists():
            not_found.append(uid)
            continue
        if update_and_ingest(fp, prompts):
            print(f"✅ {uid}: {len(prompts)} prompts")
            updated += 1
        else:
            print(f"❌ {uid}: failed")
    print(f"\n📊 Summary: {updated} updated")
    if not_found:
        print(f"⚠️  Not found: {', '.join(not_found)}")

if __name__ == "__main__":
    main()
