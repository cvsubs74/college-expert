// Mock data for landing page demos
export const demoStudent = {
    name: "Ethan Nguyen",
    grade: "Senior",
    school: "Central Valley High School",
    state: "California",
    gpa: 3.85,
    satScore: 1450,
    actScore: 32,
    activities: [
        {
            name: "Debate Team Captain",
            years: "3 years",
            leadership: true
        },
        {
            name: "Coding Club President",
            years: "2 years",
            leadership: true
        },
        {
            name: "Volunteer Tutor",
            years: "4 years",
            leadership: false
        }
    ],
    awards: [
        "National Merit Semifinalist",
        "State Debate Champion",
        "AP Scholar with Distinction"
    ]
};

export const demoUniversities = [
    {
        id: "princeton",
        name: "Princeton University",
        location: "Princeton, NJ",
        acceptanceRate: 5.8,
        ranking: 1,
        matchScore: 85,
        fitCategory: "Reach",
        tuition: "$57,410",
        logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d0/Princeton_seal.svg/200px-Princeton_seal.svg.png"
    },
    {
        id: "stanford",
        name: "Stanford University",
        location: "Stanford, CA",
        acceptanceRate: 4.3,
        ranking: 3,
        matchScore: 82,
        fitCategory: "Reach",
        tuition: "$56,169",
        logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Stanford_University_seal_2003.svg/200px-Stanford_University_seal_2003.svg.png"
    },
    {
        id: "ucla",
        name: "UCLA",
        location: "Los Angeles, CA",
        acceptanceRate: 12.3,
        ranking: 20,
        matchScore: 92,
        fitCategory: "Target",
        tuition: "$13,401",
        logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0d/The_University_of_California_UCLA.svg/200px-The_University_of_California_UCLA.svg.png"
    },
    {
        id: "ucsb",
        name: "UC Santa Barbara",
        location: "Santa Barbara, CA",
        acceptanceRate: 32.3,
        ranking: 32,
        matchScore: 95,
        fitCategory: "Safety",
        tuition: "$14,451",
        logoUrl: "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c9/UC_Santa_Barbara_seal.svg/200px-UC_Santa_Barbara_seal.svg.png"
    }
];

export const demoChatConversation = [
    {
        role: "user",
        message: "What's Princeton's computer science program like?"
    },
    {
        role: "assistant",
        message: "Princeton's Computer Science program is consistently ranked in the top 10 nationally. Key highlights:\n\n• Strong focus on algorithms and theoretical foundations\n• Average starting salary: $125,000\n• 95% job placement within 6 months\n• Top employers: Google, Meta, Microsoft, Amazon\n• Active collaboration with the Princeton Neuroscience Institute for AI research"
    }
];

export const demoDocuments = [
    {
        name: "transcript.pdf",
        size: "2.1 MB",
        status: "processing",
        extractedData: {
            gpa: 3.85,
            courses: 28,
            honors: 12
        }
    },
    {
        name: "sat_scores.pdf",
        size: "684 KB",
        status: "processing",
        extractedData: {
            total: 1450,
            math: 750,
            reading: 700
        }
    },
    {
        name: "activities.pdf",
        size: "1.5 MB",
        status: "processing",
        extractedData: {
            activities: 8,
            leadership: 3,
            volunteer: 200
        }
    }
];

export const demoFitAnalysis = {
    university: "UCLA",
    matchScore: 92,
    fitCategory: "Target",
    breakdown: {
        academics: 95,
        testScores: 90,
        extracurriculars: 88
    },
    insights: [
        "Your GPA (3.85) exceeds UCLA's average admitted student GPA (3.82)",
        "Your SAT score (1450) is at the 75th percentile for admitted students",
        "Strong leadership profile aligns with UCLA's holistic review"
    ],
    recommendation: "UCLA is a strong target school for you. Your academic profile and extracurriculars make you a competitive applicant."
};
