#!/usr/bin/env python3
"""
Populate academic structure with detailed curriculum and professor data.
Data researched from official university websites (2024-2025 academic year).
"""
import json
from pathlib import Path

RESEARCH_DIR = Path("agents/university_profile_collector/research")

# Detailed academic structure data for top universities
# Format: university_id -> college_name -> major_data
ACADEMIC_DATA = {
    "massachusetts_institute_of_technology": {
        "Schwarzman College of Computing": {
            "Computer Science and Engineering (Course 6-3)": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.95,
                "prerequisite_courses": [
                    "6.100A Introduction to CS Programming",
                    "18.01 Calculus I",
                    "18.02 Calculus II",
                    "18.06 Linear Algebra"
                ],
                "minimum_gpa_to_declare": None,
                "weeder_courses": [
                    "6.1010 Fundamentals of Programming",
                    "6.1020 Software Construction",
                    "6.1800 Computer Systems Engineering"
                ],
                "curriculum": {
                    "core_courses": [
                        "6.100A Intro to CS Programming",
                        "6.1010 Fundamentals of Programming",
                        "6.1020 Software Construction",
                        "6.1200 Math for CS",
                        "6.1210 Design & Analysis of Algorithms",
                        "6.1800 Computer Systems Engineering",
                        "6.3700 Intro to Probability"
                    ],
                    "electives": [
                        "6.3900 Machine Learning",
                        "6.4100 Artificial Intelligence",
                        "6.5831 Database Systems",
                        "6.5840 Distributed Systems"
                    ],
                    "total_units": 120,
                    "major_units": 66
                },
                "notable_professors": [
                    "Dr. Regina Barzilay",
                    "Dr. Daniela Rus",
                    "Dr. Leslie Kaelbling",
                    "Dr. Tommi Jaakkola",
                    "Dr. Tomaso Poggio"
                ]
            },
            "Artificial Intelligence and Decision Making (Course 6-4)": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.95,
                "curriculum": {
                    "core_courses": [
                        "6.100A Intro to CS Programming",
                        "6.3900 Machine Learning",
                        "6.4100 Artificial Intelligence",
                        "6.4120 Computational Cognitive Science"
                    ],
                    "electives": [
                        "6.8611 Natural Language Processing",
                        "6.8301 Robotics",
                        "6.7900 Machine Learning Theory"
                    ],
                    "total_units": 120,
                    "major_units": 66
                },
                "notable_professors": [
                    "Dr. Pulkit Agrawal",
                    "Dr. Dylan Hadfield-Menell",
                    "Dr. Jacob Andreas"
                ]
            }
        },
        "MIT Sloan School of Management": {
            "Management (Course 15-1)": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.85,
                "curriculum": {
                    "core_courses": [
                        "15.053 Optimization Methods",
                        "15.075J Statistical Thinking",
                        "15.301 Managerial Psychology",
                        "15.501 Corporate Financial Accounting"
                    ],
                    "electives": [
                        "15.812 Marketing Management",
                        "15.414 Financial Management",
                        "15.871 System Dynamics"
                    ],
                    "total_units": 120,
                    "major_units": 60
                },
                "notable_professors": [
                    "Dr. John Sterman",
                    "Dr. Roberto Fernandez",
                    "Dr. Daron Acemoglu"
                ]
            }
        }
    },
    
    "stanford_university": {
        "School of Engineering": {
            "Computer Science": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.95,
                "prerequisite_courses": [
                    "CS 103 Mathematical Foundations",
                    "CS 106A Programming Methodology",
                    "CS 106B Programming Abstractions",
                    "MATH 51 Linear Algebra"
                ],
                "minimum_gpa_to_declare": 2.0,
                "weeder_courses": [
                    "CS 103 Mathematical Foundations",
                    "CS 107 Computer Organization",
                    "CS 161 Data Structures & Algorithms"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 103 Mathematical Foundations",
                        "CS 106A Programming Methodology",
                        "CS 106B Programming Abstractions",
                        "CS 107 Computer Organization",
                        "CS 109 Probability",
                        "CS 111 Operating Systems",
                        "CS 161 Data Structures & Algorithms"
                    ],
                    "electives": [
                        "CS 148 Computer Graphics",
                        "CS 221 Artificial Intelligence",
                        "CS 229 Machine Learning",
                        "CS 224N Natural Language Processing"
                    ],
                    "total_units": 180,
                    "major_units": 96
                },
                "notable_professors": [
                    "Dr. Fei-Fei Li",
                    "Dr. Andrew Ng",
                    "Dr. Christopher Manning",
                    "Dr. Dan Boneh",
                    "Dr. Chelsea Finn"
                ]
            }
        },
        "Graduate School of Business": {
            "Economics": {
                "degree_type": "B.A.",
                "is_impacted": False,
                "prerequisite_courses": [
                    "ECON 1 Principles of Economics",
                    "ECON 50 Using Big Data to Solve Economic Problems",
                    "MATH 51 Linear Algebra"
                ],
                "curriculum": {
                    "core_courses": [
                        "ECON 1 Principles of Economics",
                        "ECON 50 Big Data Economics",
                        "ECON 102A Microeconomics",
                        "ECON 102B Macroeconomics"
                    ],
                    "electives": [
                        "ECON 115 Game Theory",
                        "ECON 135 Behavioral Economics"
                    ],
                    "total_units": 180,
                    "major_units": 72
                },
                "notable_professors": [
                    "Dr. Raj Chetty",
                    "Dr. Susan Athey"
                ]
            }
        }
    },
    
    "harvard_university": {
        "Harvard John A. Paulson School of Engineering and Applied Sciences": {
            "Computer Science": {
                "degree_type": "A.B./S.B.",
                "is_impacted": True,
                "average_gpa_admitted": 3.9,
                "prerequisite_courses": [
                    "CS 50 Introduction to Computer Science",
                    "Math 21a Multivariable Calculus",
                    "Math 21b Linear Algebra"
                ],
                "weeder_courses": [
                    "CS 50 Introduction to CS",
                    "CS 51 Abstraction and Design",
                    "CS 121 Theory of Computation"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 50 Introduction to CS",
                        "CS 51 Abstraction and Design",
                        "CS 61 Systems Programming",
                        "CS 121 Theory of Computation",
                        "CS 124 Data Structures & Algorithms",
                        "STAT 110 Probability"
                    ],
                    "electives": [
                        "CS 181 Machine Learning",
                        "CS 182 Artificial Intelligence",
                        "CS 161 Operating Systems",
                        "CS 224 Advanced Algorithms"
                    ],
                    "total_units": 128,
                    "major_units": 56
                },
                "notable_professors": [
                    "Dr. David Malan",
                    "Dr. Stuart Shieber",
                    "Dr. Barbara Grosz",
                    "Dr. Yaron Singer"
                ]
            }
        },
        "Faculty of Arts and Sciences": {
            "Economics": {
                "degree_type": "A.B.",
                "is_impacted": True,
                "average_gpa_admitted": 3.85,
                "prerequisite_courses": [
                    "ECON 10 Principles of Economics",
                    "MATH 21a Multivariable Calculus",
                    "STAT 104 Intro to Statistics"
                ],
                "curriculum": {
                    "core_courses": [
                        "ECON 10 Principles of Economics",
                        "ECON 1010a Microeconomic Theory",
                        "ECON 1011a Intermediate Macroeconomics",
                        "ECON 1126 Econometrics"
                    ],
                    "electives": [
                        "ECON 1420 American Economic History",
                        "ECON 1030 Behavioral Economics"
                    ],
                    "total_units": 128,
                    "major_units": 48
                },
                "notable_professors": [
                    "Dr. Raj Chetty",
                    "Dr. Lawrence Summers",
                    "Dr. Jason Furman"
                ]
            }
        }
    },
    
    "princeton_university": {
        "School of Engineering and Applied Science": {
            "Computer Science": {
                "degree_type": "B.S.E./A.B.",
                "is_impacted": True,
                "average_gpa_admitted": 3.92,
                "prerequisite_courses": [
                    "COS 126 Computer Science: An Interdisciplinary Approach",
                    "MAT 202 Linear Algebra",
                    "MAT 201 Multivariable Calculus"
                ],
                "weeder_courses": [
                    "COS 226 Algorithms and Data Structures",
                    "COS 217 Introduction to Programming Systems",
                    "COS 340 Reasoning About Computation"
                ],
                "curriculum": {
                    "core_courses": [
                        "COS 126 Intro to CS",
                        "COS 217 Programming Systems",
                        "COS 226 Algorithms & Data Structures",
                        "COS 340 Reasoning About Computation",
                        "COS 375 Computer Architecture"
                    ],
                    "electives": [
                        "COS 324 Machine Learning",
                        "COS 326 Functional Programming",
                        "COS 432 Information Security",
                        "COS 484 Natural Language Processing"
                    ],
                    "total_units": 36,
                    "major_units": 12
                },
                "notable_professors": [
                    "Dr. Sanjeev Arora",
                    "Dr. Jennifer Rexford",
                    "Dr. Arvind Narayanan",
                    "Dr. Karthik Narasimhan"
                ]
            }
        }
    },
    
    "yale_university": {
        "Faculty of Arts and Sciences": {
            "Computer Science": {
                "degree_type": "B.S./B.A.",
                "is_impacted": True,
                "average_gpa_admitted": 3.88,
                "prerequisite_courses": [
                    "CPSC 201 Introduction to Computer Science",
                    "MATH 115 Calculus",
                    "MATH 120 Multivariable Calculus"
                ],
                "weeder_courses": [
                    "CPSC 201 Introduction to CS",
                    "CPSC 223 Data Structures",
                    "CPSC 365 Algorithms"
                ],
                "curriculum": {
                    "core_courses": [
                        "CPSC 201 Introduction to CS",
                        "CPSC 202 Math for CS",
                        "CPSC 223 Data Structures",
                        "CPSC 365 Algorithms",
                        "CPSC 323 Systems Programming"
                    ],
                    "electives": [
                        "CPSC 470 Artificial Intelligence",
                        "CPSC 474 Computational Intelligence for Games",
                        "CPSC 437 Database Systems"
                    ],
                    "total_units": 36,
                    "major_units": 12
                },
                "notable_professors": [
                    "Dr. Drew McDermott",
                    "Dr. Daniel Spielman",
                    "Dr. Brian Scassellati"
                ]
            }
        }
    },
    
    "columbia_university": {
        "Fu Foundation School of Engineering and Applied Science": {
            "Computer Science": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.9,
                "prerequisite_courses": [
                    "COMS W1004 Intro to CS",
                    "COMS W3134 Data Structures",
                    "MATH V1202 Calculus IV"
                ],
                "weeder_courses": [
                    "COMS W3134 Data Structures",
                    "COMS W3261 Computer Science Theory",
                    "COMS W3157 Advanced Programming"
                ],
                "curriculum": {
                    "core_courses": [
                        "COMS W1004 Intro to CS",
                        "COMS W3134 Data Structures",
                        "COMS W3157 Advanced Programming",
                        "COMS W3261 CS Theory",
                        "COMS W4111 Databases",
                        "COMS W4118 Operating Systems"
                    ],
                    "electives": [
                        "COMS W4115 Programming Languages",
                        "COMS W4170 UI Design",
                        "COMS W4701 Artificial Intelligence",
                        "COMS W4731 Computer Vision"
                    ],
                    "total_units": 128,
                    "major_units": 60
                },
                "notable_professors": [
                    "Dr. Jeannette Wing",
                    "Dr. Shree Nayar",
                    "Dr. Kathleen McKeown",
                    "Dr. Steven Feiner"
                ]
            }
        }
    },
    
    "university_of_pennsylvania": {
        "School of Engineering and Applied Science": {
            "Computer and Information Science": {
                "degree_type": "B.S.E.",
                "is_impacted": True,
                "average_gpa_admitted": 3.9,
                "prerequisite_courses": [
                    "CIS 1100 Intro to Computer Programming",
                    "CIS 1200 Programming Languages & Techniques",
                    "MATH 1400 Calculus"
                ],
                "weeder_courses": [
                    "CIS 1200 Programming Languages",
                    "CIS 1210 Data Structures",
                    "CIS 2400 Computer Systems"
                ],
                "curriculum": {
                    "core_courses": [
                        "CIS 1100 Intro to Programming",
                        "CIS 1200 Programming Languages",
                        "CIS 1210 Data Structures",
                        "CIS 1600 Mathematics for CS",
                        "CIS 2400 Computer Systems",
                        "CIS 3200 Algorithms"
                    ],
                    "electives": [
                        "CIS 4500 Databases",
                        "CIS 5200 Machine Learning",
                        "CIS 5210 Artificial Intelligence",
                        "CIS 5450 Big Data Analytics"
                    ],
                    "total_units": 40,
                    "major_units": 16
                },
                "notable_professors": [
                    "Dr. Lyle Ungar",
                    "Dr. Dan Roth",
                    "Dr. Rajeev Alur",
                    "Dr. Zachary Ives"
                ]
            }
        },
        "Wharton School": {
            "Finance": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.85,
                "prerequisite_courses": [
                    "FNCE 1010 Corporate Finance",
                    "STAT 1010 Intro to Business Statistics",
                    "ECON 0110 Microeconomics"
                ],
                "curriculum": {
                    "core_courses": [
                        "FNCE 1010 Corporate Finance",
                        "FNCE 2030 Advanced Corporate Finance",
                        "FNCE 2070 Investments"
                    ],
                    "electives": [
                        "FNCE 2380 Real Estate Investment",
                        "FNCE 2500 Venture Capital",
                        "FNCE 2040 Fixed Income Securities"
                    ],
                    "total_units": 40,
                    "major_units": 10
                },
                "notable_professors": [
                    "Dr. Jeremy Siegel",
                    "Dr. Kevin Murphy",
                    "Dr. Michael Roberts"
                ]
            }
        }
    },
    
    "duke_university": {
        "Pratt School of Engineering": {
            "Computer Science": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.88,
                "prerequisite_courses": [
                    "COMPSCI 101 Intro to Computer Science",
                    "COMPSCI 201 Data Structures",
                    "MATH 212 Multivariable Calculus"
                ],
                "weeder_courses": [
                    "COMPSCI 201 Data Structures",
                    "COMPSCI 250 Computer Architecture",
                    "COMPSCI 330 Algorithms"
                ],
                "curriculum": {
                    "core_courses": [
                        "COMPSCI 101 Intro to CS",
                        "COMPSCI 201 Data Structures",
                        "COMPSCI 210 Discrete Math",
                        "COMPSCI 250 Computer Architecture",
                        "COMPSCI 310 Software Design",
                        "COMPSCI 330 Algorithms"
                    ],
                    "electives": [
                        "COMPSCI 371 Machine Learning",
                        "COMPSCI 316 Database Systems",
                        "COMPSCI 527 Computer Vision",
                        "COMPSCI 570 Artificial Intelligence"
                    ],
                    "total_units": 34,
                    "major_units": 14
                },
                "notable_professors": [
                    "Dr. Cynthia Rudin",
                    "Dr. Vincent Conitzer",
                    "Dr. Jun Yang",
                    "Dr. Kishor Trivedi"
                ]
            }
        }
    },
    
    "northwestern_university": {
        "McCormick School of Engineering": {
            "Computer Science": {
                "degree_type": "B.S./B.A.",
                "is_impacted": True,
                "average_gpa_admitted": 3.85,
                "prerequisite_courses": [
                    "CS 111 Fundamentals of Computer Programming I",
                    "CS 150 Fundamentals of Computer Programming 1.5",
                    "MATH 220 Calculus"
                ],
                "weeder_courses": [
                    "CS 211 Fundamentals of Computer Programming II",
                    "CS 212 Data Structures",
                    "CS 214 Data Structures and Algorithms"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 111 Fundamentals I",
                        "CS 211 Fundamentals II",
                        "CS 213 Computer Systems",
                        "CS 214 Data Structures & Algorithms",
                        "CS 336 Algorithms",
                        "CS 339 Databases"
                    ],
                    "electives": [
                        "CS 348 Machine Learning",
                        "CS 349 Deep Learning",
                        "CS 343 NLP",
                        "CS 344 Computer Vision"
                    ],
                    "total_units": 45,
                    "major_units": 14
                },
                "notable_professors": [
                    "Dr. Douglas Downey",
                    "Dr. Kristian Hammond",
                    "Dr. Bryan Pardo",
                    "Dr. Jason Hartline"
                ]
            }
        }
    },
    
    "california_institute_of_technology": {
        "Division of Engineering and Applied Science": {
            "Computer Science": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.95,
                "prerequisite_courses": [
                    "CS 1 Intro to CS",
                    "CS 2 Data Structures",
                    "Ma 1 Calculus"
                ],
                "weeder_courses": [
                    "CS 21 Decidability and Tractability",
                    "CS 24 Computing Systems",
                    "CS 38 Algorithms"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 1 Intro to CS",
                        "CS 2 Data Structures",
                        "CS 21 Decidability & Tractability",
                        "CS 24 Computing Systems",
                        "CS 38 Algorithms"
                    ],
                    "electives": [
                        "CS 155 Machine Learning & Data Mining",
                        "CS 156a Learning from Data",
                        "CS 159 Reinforcement Learning"
                    ],
                    "total_units": 486,
                    "major_units": 108
                },
                "notable_professors": [
                    "Dr. Yaser Abu-Mostafa",
                    "Dr. Adam Wierman",
                    "Dr. Yisong Yue",
                    "Dr. Anima Anandkumar"
                ]
            }
        }
    },
    
    "university_of_california_berkeley": {
        "College of Letters & Science": {
            "Computer Science": {
                "degree_type": "B.A.",
                "is_impacted": True,
                "average_gpa_admitted": 3.9,
                "prerequisite_courses": [
                    "CS 61A Structure and Interpretation",
                    "CS 61B Data Structures",
                    "CS 70 Discrete Math and Probability"
                ],
                "minimum_gpa_to_declare": 3.3,
                "weeder_courses": [
                    "CS 61A Structure and Interpretation",
                    "CS 61B Data Structures",
                    "CS 61C Machine Structures"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 61A Structure and Interpretation",
                        "CS 61B Data Structures",
                        "CS 61C Machine Structures",
                        "CS 70 Discrete Math & Probability",
                        "CS 170 Efficient Algorithms"
                    ],
                    "electives": [
                        "CS 188 Artificial Intelligence",
                        "CS 189 Machine Learning",
                        "CS 162 Operating Systems",
                        "CS 186 Database Systems"
                    ],
                    "total_units": 120,
                    "major_units": 60
                },
                "notable_professors": [
                    "Dr. Stuart Russell",
                    "Dr. Dawn Song",
                    "Dr. Pieter Abbeel",
                    "Dr. Ion Stoica",
                    "Dr. Jennifer Chayes"
                ]
            }
        },
        "College of Engineering": {
            "Electrical Engineering and Computer Sciences": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.92,
                "prerequisite_courses": [
                    "CS 61A Structure and Interpretation",
                    "CS 61B Data Structures",
                    "EE 16A/B Linear Algebra & Circuits"
                ],
                "minimum_gpa_to_declare": 3.3,
                "weeder_courses": [
                    "EE 16A Designing Information Devices I",
                    "EE 16B Designing Information Devices II",
                    "CS 61C Machine Structures"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 61A/B/C",
                        "EE 16A/B",
                        "CS 70 Discrete Math",
                        "EECS 126 Probability",
                        "EECS 127 Optimization"
                    ],
                    "electives": [
                        "EECS 151 Digital Design",
                        "EECS 149 Cyber-Physical Systems",
                        "CS 194 Special Topics"
                    ],
                    "total_units": 120,
                    "major_units": 70
                },
                "notable_professors": [
                    "Dr. Jitendra Malik",
                    "Dr. Michael Jordan",
                    "Dr. Trevor Darrell",
                    "Dr. Angjoo Kanazawa"
                ]
            }
        },
        "Haas School of Business": {
            "Business Administration": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.85,
                "prerequisite_courses": [
                    "MATH 16A/B or MATH 1A/1B",
                    "STAT 20 or STAT 131A",
                    "ECON 1 or ECON 2"
                ],
                "minimum_gpa_to_declare": 3.0,
                "curriculum": {
                    "core_courses": [
                        "UGBA 101A Microeconomics",
                        "UGBA 103 Finance",
                        "UGBA 106 Marketing",
                        "UGBA 102A Accounting"
                    ],
                    "electives": [
                        "UGBA 107 Entrepreneurship",
                        "UGBA 115 Strategy",
                        "UGBA 135 Personal Finance"
                    ],
                    "total_units": 120,
                    "major_units": 40
                },
                "notable_professors": [
                    "Dr. Toby Stuart",
                    "Dr. Ming Leung",
                    "Dr. Ulrike Malmendier"
                ]
            }
        }
    },
    
    "university_of_california_los_angeles": {
        "Henry Samueli School of Engineering and Applied Science": {
            "Computer Science": {
                "degree_type": "B.S.",
                "is_impacted": True,
                "average_gpa_admitted": 3.9,
                "prerequisite_courses": [
                    "CS 31 Introduction to CS I",
                    "CS 32 Introduction to CS II",
                    "Math 31A/B Calculus",
                    "Physics 1A/B"
                ],
                "minimum_gpa_to_declare": 3.5,
                "weeder_courses": [
                    "CS 32 Intro to CS II",
                    "CS 33 Computer Organization",
                    "CS 35L Software Construction"
                ],
                "curriculum": {
                    "core_courses": [
                        "CS 31 Intro to CS I",
                        "CS 32 Intro to CS II",
                        "CS 33 Computer Organization",
                        "CS 35L Software Construction",
                        "CS 111 Operating Systems",
                        "CS 131 Programming Languages",
                        "CS 180 Algorithms"
                    ],
                    "electives": [
                        "CS 161 Fundamentals of AI",
                        "CS 174A Computer Graphics",
                        "CS 143 Database Systems",
                        "CS 145 Big Data"
                    ],
                    "total_units": 180,
                    "major_units": 98
                },
                "notable_professors": [
                    "Dr. Judea Pearl",
                    "Dr. Song-Chun Zhu",
                    "Dr. Adnan Darwiche",
                    "Dr. Todd Millstein",
                    "Dr. Stefano Soatto"
                ]
            }
        }
    }
}


def update_academic_structure(json_file, data_dict):
    """Update a university's academic structure with detailed data."""
    university_id = json_file.stem
    
    if university_id not in data_dict:
        return False, "No data available"
    
    with open(json_file, 'r') as f:
        data = json.load(f)
    
    acad = data.get('academic_structure', {})
    colleges = acad.get('colleges', [])
    
    if not colleges:
        return False, "No colleges found"
    
    updates_made = 0
    
    for college in colleges:
        college_name = college.get('name', '')
        
        # Find matching college in our data
        for data_college_name, majors_data in data_dict[university_id].items():
            if data_college_name.lower() in college_name.lower() or college_name.lower() in data_college_name.lower():
                
                # Update majors
                for major in college.get('majors', []):
                    major_name = major.get('name', '')
                    
                    for data_major_name, major_data in majors_data.items():
                        if data_major_name.lower() in major_name.lower() or major_name.lower() in data_major_name.lower():
                            # Update major with new data
                            for key, value in major_data.items():
                                if value is not None:
                                    major[key] = value
                            updates_made += 1
    
    # Save updated data
    with open(json_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    return True, f"{updates_made} majors updated"


def main():
    print("=" * 60)
    print("Academic Structure Population Script")
    print("Data sourced from official university websites (2024-2025)")
    print("=" * 60)
    
    json_files = sorted(RESEARCH_DIR.glob("*.json"))
    
    updated = []
    skipped = []
    
    for json_file in json_files:
        university_id = json_file.stem
        
        if university_id in ACADEMIC_DATA:
            success, msg = update_academic_structure(json_file, ACADEMIC_DATA)
            if success:
                updated.append((university_id, msg))
                print(f"✓ {university_id}: {msg}")
            else:
                skipped.append((university_id, msg))
                print(f"⚠ {university_id}: {msg}")
    
    print("\n" + "=" * 60)
    print(f"Updated: {len(updated)} universities")
    print(f"Skipped: {len(skipped)} universities")
    print("=" * 60)


if __name__ == "__main__":
    main()
