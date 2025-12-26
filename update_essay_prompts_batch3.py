#!/usr/bin/env python3
"""Batch 3: More university essay prompts."""
import json
import requests
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

KNOWN_PROMPTS = {
    # Caltech
    "california_institute_of_technology": [
        {
            "prompt": "If you had to choose an area of STEM interest today, what would you choose and why?",
            "word_limit": "100-200 words",
            "type": "Major",
            "required": True
        },
        {
            "prompt": "Tell us about a STEM-related experience from the last few years and share how and why it inspired your curiosity.",
            "word_limit": "100-200 words",
            "type": "STEM",
            "required": True
        },
        {
            "prompt": "Take this opportunity to nerd out and talk about whatever STEM rabbit hole you have found yourself falling into.",
            "word_limit": "150 words",
            "type": "STEM",
            "required": True
        },
        {
            "prompt": "How have you been a creator, inventor, or innovator in your own life?",
            "word_limit": "250 words",
            "type": "Innovation",
            "required": True
        },
        {
            "prompt": "Caltech's values include respect for a diversity of thoughts and ideas. How have you cultivated this value in your own life?",
            "word_limit": "200 words",
            "type": "Values",
            "required": True
        }
    ],
    # William & Mary
    "the_college_of_william_and_mary": [
        {
            "prompt": "Are there any particular communities that are important to you, and how do you see yourself being a part of our community?",
            "word_limit": "300 words",
            "type": "Community",
            "required": False
        },
        {
            "prompt": "Share more about a personal academic interest or career goal.",
            "word_limit": "300 words",
            "type": "Academic",
            "required": False
        },
        {
            "prompt": "What led to your interest in William & Mary?",
            "word_limit": "300 words",
            "type": "Why W&M",
            "required": False
        }
    ],
    # Brandeis
    "brandeis_university": [
        {
            "prompt": "Brandeis was established 75 years ago to address antisemitism, racism, and gender discrimination in higher education. How has your educational experience shaped your perspective on inclusivity and justice?",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # Fordham
    "fordham_university": [
        {
            "prompt": "Share an experience that caused you to develop a new perspective, change your point of view, and/or empowered you to take action or be courageous.",
            "word_limit": "300 words",
            "type": "Personal Growth",
            "required": False
        },
        {
            "prompt": "Fordham's motto is 'New York is my campus, Fordham is my school.' What has prepared you to embrace the unique opportunity of living and learning in New York City?",
            "word_limit": "300 words",
            "type": "Why Fordham",
            "required": False
        }
    ],
    # George Washington
    "george_washington_university": [
        {
            "prompt": "Every applicant can choose from one of the following two prompts to submit an essay. At the George Washington University, our students frequently interact with policymakers, world leaders, and influencers. How do you hope to engage in this environment?",
            "word_limit": "500 words",
            "type": "Why GW",
            "required": True
        }
    ],
    # Syracuse
    "syracuse_university": [
        {
            "prompt": "Syracuse University is a place that is very serious about our commitment to ideas, our shared humanity, and learning. Why is Syracuse University a good fit for you?",
            "word_limit": "250 words",
            "type": "Why Syracuse",
            "required": True
        }
    ],
    # Texas A&M
    "texas_a_m_university": [
        {
            "prompt": "Describe a life event which you feel has prepared you to be successful in college.",
            "word_limit": "250 words",
            "type": "Personal",
            "required": True
        },
        {
            "prompt": "Tell us about the person who has most impacted your life and why.",
            "word_limit": "250 words",
            "type": "Personal",
            "required": True
        }
    ],
    # Indiana University
    "indiana_university_bloomington": [
        {
            "prompt": "Please briefly elaborate on one of your extracurricular activities or work experiences.",
            "word_limit": "200-400 words",
            "type": "Activity",
            "required": False
        }
    ],
    # Ohio State
    "ohio_state_university": [
        {
            "prompt": "Please describe your academic and non-academic interests to the admissions committee. Why do you want to attend Ohio State?",
            "word_limit": "250-500 words",
            "type": "Why Ohio State",
            "required": True
        }
    ],
    # Penn State
    "pennsylvania_state_university": [
        {
            "prompt": "Please tell us something about yourself, your experiences, or activities that you believe would reflect positively on your ability to succeed at Penn State.",
            "word_limit": "500 words",
            "type": "Personal",
            "required": False
        }
    ],
    # Florida State
    "florida_state_university": [
        {
            "prompt": "Florida State University is a community that is dedicated to scholarship, creativity, and the exchange of ideas. What unique perspective will you bring to FSU?",
            "word_limit": "250 words",
            "type": "Why FSU",
            "required": True
        }
    ],
    # Clemson
    "clemson_university": [
        {
            "prompt": "Clemson University's core principles are honesty, integrity, and mutual respect. Share a time when you demonstrated one or more of these principles.",
            "word_limit": "250 words",
            "type": "Values",
            "required": True
        }
    ],
    # Baylor
    "baylor_university": [
        {
            "prompt": "Baylor University is known for its quality academics, its strong Christian mission, and its caring community. What about Baylor University appeals to you?",
            "word_limit": "500 words",
            "type": "Why Baylor",
            "required": False
        }
    ],
    # Howard
    "howard_university": [
        {
            "prompt": "Howard University has prided itself on preparing students like you for leadership and service. Describe how Howard can specifically contribute to your future plans.",
            "word_limit": "500 words",
            "type": "Why Howard",
            "required": True
        }
    ],
    # Santa Clara
    "santa_clara_university": [
        {
            "prompt": "At Santa Clara University, we push our students to be creative, be challenged, and be the solution. What qualities do you possess that will enable you to contribute to the SCU experience?",
            "word_limit": "300 words",
            "type": "Why SCU",
            "required": True
        }
    ],
    # Marquette
    "marquette_university": [
        {
            "prompt": "Describe a meaningful experience that has shaped your identity or worldview. How would you leverage this experience at Marquette University to create a more diverse and inclusive community?",
            "word_limit": "500 words",
            "type": "Identity",
            "required": True
        }
    ],
    # Gonzaga
    "gonzaga_university": [
        {
            "prompt": "At Gonzaga, we believe in the whole person. What makes you uniquely you, and how will you share that with our community?",
            "word_limit": "300 words",
            "type": "Personal",
            "required": True
        }
    ],
    # American University
    "american_university": [
        {
            "prompt": "American University is deeply committed to creating a culture of inclusion and equity. How do you envision yourself contributing to this vision on our campus? Please share a time when you've contributed to creating a more inclusive environment.",
            "word_limit": "250 words",
            "type": "Community",
            "required": True
        }
    ],
    # Drexel
    "drexel_university": [
        {
            "prompt": "Tell us about your experiences with cooperative education (co-ops), internships, or jobs where you applied classroom knowledge to real-world situations.",
            "word_limit": "250 words",
            "type": "Experience",
            "required": False
        }
    ],
    # RPI
    "rensselaer_polytechnic_institute": [
        {
            "prompt": "Describe why you wish to study at Rensselaer and how you see yourself being part of the Rensselaer community.",
            "word_limit": "250 words",
            "type": "Why RPI",
            "required": True
        }
    ],
    # RIT
    "rochester_institute_of_technology": [
        {
            "prompt": "RIT seeks students who are fascinated by possibilities and passionate about innovation. How do you envision yourself contributing to RIT's culture of creativity and discovery?",
            "word_limit": "250 words",
            "type": "Why RIT",
            "required": True
        }
    ],
    # Stony Brook
    "stony_brook_university": [
        {
            "prompt": "Stony Brook students are known for their boldness and commitment to excellence. What inspires you to thrive in our challenging academic environment?",
            "word_limit": "250 words",
            "type": "Why Stony Brook",
            "required": False
        }
    ],
    # Chapman
    "chapman_university": [
        {
            "prompt": "Chapman seeks curious, motivated students who look for innovative, collaborative ways to think about and solve problems. Share an example of when you discovered a unique approach to a challenge.",
            "word_limit": "250 words",
            "type": "Innovation",
            "required": True
        }
    ],
    # Loyola Marymount
    "loyola_marymount_university": [
        {
            "prompt": "Tell us about one of your core values and how you have demonstrated it in your life, activities, or community.",
            "word_limit": "500 words",
            "type": "Values",
            "required": True
        }
    ],
    # Colorado School of Mines
    "colorado_school_of_mines": [
        {
            "prompt": "Why do you want to study your intended major at Mines? What about Mines appeals to you?",
            "word_limit": "500 words",
            "type": "Why Mines",
            "required": True
        }
    ],
    # Rutgers
    "rutgers_university_new_brunswick": [
        {
            "prompt": "Please share with us why you feel Rutgers, The State University of New Jersey, provides an ideal environment for you to meet your academic goals.",
            "word_limit": "250 words",
            "type": "Why Rutgers",
            "required": False
        }
    ],
    # Arizona State
    "arizona_state_university": [
        {
            "prompt": "ASU is inspired by a spirit of innovation. Share an example of a time when you thought creatively to solve a problem.",
            "word_limit": "250 words",
            "type": "Innovation",
            "required": False
        }
    ],
    # NC State
    "north_carolina_state_university": [
        {
            "prompt": "Explain why you selected the first-choice program on your application and how it connects to your future goals or interests.",
            "word_limit": "250 words",
            "type": "Major",
            "required": True
        }
    ],
    # Michigan State
    "michigan_state_university": [
        {
            "prompt": "MSU understands that students' experiences are often affected by their socioeconomic, cultural, and racial background. If this resonates with you, feel free to share how your experiences have shaped who you are today.",
            "word_limit": "300 words",
            "type": "Background",
            "required": False
        }
    ],
    # Auburn
    "auburn_university": [
        {
            "prompt": "Auburn has a long tradition of community and belonging. If accepted, how do you plan to add to and foster Auburn's sense of community and belonging?",
            "word_limit": "250 words",
            "type": "Community",
            "required": True
        }
    ]
}


def update_university_prompts(filepath: Path, prompts: list) -> bool:
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
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        response = requests.post(KB_URL, json={"profile": profile}, headers={"Content-Type": "application/json"}, timeout=300)
        if response.ok:
            return response.json().get('success', False)
        return False
    except Exception as e:
        print(f"Error ingesting {filepath}: {e}")
        return False


def main():
    updated = ingested = 0
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
    print(f"\n📊 Summary: Updated {updated}, Ingested {ingested}")
    if not_found:
        print(f"⚠️  Not found: {', '.join(not_found)}")


if __name__ == "__main__":
    main()
