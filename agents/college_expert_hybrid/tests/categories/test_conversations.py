"""
Multi-Turn Conversation Tests - Context retention across multiple turns.
"""
from ..core import ConversationTurn, MultiTurnConversation

CATEGORY = "Multi-Turn Conversations"

TESTS = [
    # Conversation 1: University Research Flow
    MultiTurnConversation(
        conv_id="university_research_flow",
        description="User researches a university across multiple turns",
        turns=[
            ConversationTurn(
                user_message="Tell me about UC Berkeley",
                criteria=[
                    "Provides information about UC Berkeley",
                    "Mentions key facts (rankings, programs, location)",
                ],
                description="Initial university inquiry"
            ),
            ConversationTurn(
                user_message="What are its acceptance rates?",
                criteria=[
                    "References UC Berkeley (not a different school)",
                    "Provides acceptance rate information",
                ],
                description="Follow-up about same university"
            ),
            ConversationTurn(
                user_message="What majors is it known for?",
                criteria=[
                    "Still discussing UC Berkeley",
                    "Lists notable majors or programs",
                ],
                description="Further follow-up"
            ),
            ConversationTurn(
                user_message="How does it compare to UCLA?",
                criteria=[
                    "Compares UC Berkeley with UCLA",
                    "References the previous discussion about Berkeley",
                ],
                description="Comparison referencing context"
            ),
        ]
    ),
    
    # Conversation 2: Personalized Fit Analysis Flow
    MultiTurnConversation(
        conv_id="fit_analysis_flow",
        description="User gets fit analysis and follows up with questions",
        requires_profile=True,
        turns=[
            ConversationTurn(
                user_message="Analyze my fit for Stanford",
                criteria=[
                    "Provides fit analysis for Stanford",
                    "Uses student profile data",
                ],
                description="Initial fit request"
            ),
            ConversationTurn(
                user_message="Why did you categorize it that way?",
                criteria=[
                    "Explains the reasoning for the fit category",
                    "References specific factors from the analysis",
                ],
                description="Follow-up asking for explanation"
            ),
            ConversationTurn(
                user_message="What can I do to improve my chances?",
                criteria=[
                    "Provides improvement suggestions",
                    "Relates advice to Stanford specifically",
                ],
                description="Actionable improvement advice"
            ),
        ]
    ),
    
    # Conversation 3: College List Building
    MultiTurnConversation(
        conv_id="college_list_building",
        description="User builds and discusses their college list",
        requires_profile=True,
        turns=[
            ConversationTurn(
                user_message="Show me my college list",
                criteria=[
                    "Retrieves or mentions the college list",
                    "Offers to help if list is empty",
                ],
                description="Check current list"
            ),
            ConversationTurn(
                user_message="What safety schools would you recommend?",
                criteria=[
                    "Suggests safety school options",
                    "Bases recommendations on profile",
                ],
                description="Request safety school recommendations"
            ),
            ConversationTurn(
                user_message="How about reach schools?",
                criteria=[
                    "Now discusses reach schools",
                    "Maintains context from safety school discussion",
                ],
                description="Switch to reach schools"
            ),
            ConversationTurn(
                user_message="Between those options, which would you prioritize?",
                criteria=[
                    "References the schools mentioned in previous turns",
                    "Provides prioritization advice",
                ],
                description="Ask for prioritization across discussed schools"
            ),
        ]
    ),
    
    # Conversation 4: Deep Dive on Specific Topic
    MultiTurnConversation(
        conv_id="engineering_deep_dive",
        description="User explores engineering programs in depth",
        requires_profile=True,
        turns=[
            ConversationTurn(
                user_message="I'm interested in studying engineering. What are the best schools in California?",
                criteria=[
                    "Lists top California engineering schools",
                    "Provides relevant details",
                ],
                description="Initial engineering inquiry"
            ),
            ConversationTurn(
                user_message="What about Berkeley specifically?",
                criteria=[
                    "Focuses on UC Berkeley engineering",
                    "Builds on previous engineering context",
                ],
                description="Drill down to specific school"
            ),
            ConversationTurn(
                user_message="What's special about their EECS program?",
                criteria=[
                    "Discusses Berkeley EECS specifically",
                    "Provides specific program details",
                ],
                description="Further drill down to specific program"
            ),
            ConversationTurn(
                user_message="What are my chances there?",
                criteria=[
                    "Understands 'there' refers to Berkeley EECS",
                    "Attempts fit analysis or asks for profile",
                ],
                description="Pronoun resolution test"
            ),
        ]
    ),
    
    # Conversation 5: Long Context Retention (6 turns)
    MultiTurnConversation(
        conv_id="long_context_retention",
        description="Extended conversation testing long context retention",
        requires_profile=True,
        turns=[
            ConversationTurn(
                user_message="I'm looking at business schools. What options do I have?",
                criteria=[
                    "Addresses business school options",
                    "May ask clarifying questions",
                ],
                description="Start with business schools"
            ),
            ConversationTurn(
                user_message="I prefer California schools",
                criteria=[
                    "Narrows to California business schools",
                    "Remembers business focus",
                ],
                description="Add location constraint"
            ),
            ConversationTurn(
                user_message="What about USC?",
                criteria=[
                    "Discusses USC Marshall School of Business",
                    "Maintains business school context",
                ],
                description="Ask about specific school"
            ),
            ConversationTurn(
                user_message="How does it compare to UCLA Anderson?",
                criteria=[
                    "Compares USC Marshall to UCLA Anderson",
                    "Maintains business context",
                ],
                description="Compare two business schools"
            ),
            ConversationTurn(
                user_message="Which one would be better for marketing?",
                criteria=[
                    "References the two schools being discussed",
                    "Focuses on marketing specialization",
                ],
                description="Add specialization filter"
            ),
            ConversationTurn(
                user_message="Based on my profile, which should I apply to first?",
                criteria=[
                    "Uses profile for personalized advice",
                    "References schools from the entire conversation",
                ],
                description="Final personalized recommendation"
            ),
        ]
    ),
]
