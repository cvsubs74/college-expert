"""
University Acronym Mapping

This module provides a mapping of common university acronyms and abbreviations
to their corresponding unique University IDs in the knowledge base.
This helps resolve ambiguity in user queries (e.g., "USC" -> "University of Southern California").
"""

ACRONYM_MAP = {
    # California
    "USC": "university_of_southern_california",
    "UCLA": "university_of_california_los_angeles",
    "UCB": "university_of_california_berkeley",
    "BERKELEY": "university_of_california_berkeley",
    "CAL": "university_of_california_berkeley",
    "UCI": "university_of_california_irvine",
    "UCSD": "university_of_california_san_diego",
    "UCSB": "university_of_california_santa_barbara",
    "UCD": "university_of_california_davis",
    "UCSC": "university_of_california_santa_cruz",
    "UCR": "university_of_california_riverside",
    "UCM": "university_of_california_merced",
    "STANFORD": "stanford_university",
    "CALTECH": "california_institute_of_technology",
    
    # East Coast
    "MIT": "massachusetts_institute_of_technology",
    "NYU": "new_york_university",
    "HARVARD": "harvard_university_slug",
    "CMU": "carnegie_mellon_university",
    "UPENN": "university_of_pennsylvania",
    "PENN": "university_of_pennsylvania",
    "COLUMBIA": "columbia_university",
    "CORNELL": "cornell_university",
    "YALE": "yale_university",
    "PRINCETON": "princeton_university",
    "BROWN": "brown_university",
    "DARTMOUTH": "dartmouth_college",
    
    # South/Midwest/Other
    "GT": "georgia_institute_of_technology",
    "GEORGIA TECH": "georgia_institute_of_technology",
    "GATECH": "georgia_institute_of_technology",
    "UIUC": "university_of_illinois_urbana_champaign",
    "UNC": "university_of_north_carolina_at_chapel_hill",
    "UT AUSTIN": "university_of_texas_at_austin",
    "UT": "university_of_texas_at_austin",
    "UMICH": "university_of_michigan",
    "MICHIGAN": "university_of_michigan",
    "UW": "university_of_wisconsin-madison", # Note: Ambiguous, but mapping to Madison as primary
    "WISCONSIN": "university_of_wisconsin-madison",
    "PURDUE": "Purdue_University",
    "UF": "university_of_florida_slug",
    "UFL": "university_of_florida_slug",
}
