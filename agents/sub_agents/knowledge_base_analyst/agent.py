"""
Knowledge Base Analyst - Searches and manages college admissions knowledge base using File Search.
Uses sequential pattern: retriever -> formatter
"""
from google.adk.agents import LlmAgent, SequentialAgent
from ...tools.file_search_tools import search_knowledge_base
from ...tools.document_management_tools import list_documents
from ...schemas import KnowledgeBaseOutput
from ...tools.logging_utils import log_agent_entry, log_agent_exit


# Retriever agent - calls the tool and stores raw data
knowledge_base_retriever = LlmAgent(
    name="knowledge_base_retriever",
    model="gemini-2.5-flash",
    description="Retrieves information from college admissions knowledge base and manages documents",
    instruction="""
    You retrieve information from the college admissions knowledge base.

    **AVAILABLE TOOLS:**
    1. `search_knowledge_base(query)` - Search the knowledge base for information
    2. `list_documents()` - List all documents in the knowledge base

    **YOUR JOB:**
    - If the user asks a question, call `search_knowledge_base` with the query
    - If the user wants to see what's in the knowledge base, call `list_documents`
    - Store the raw response in the state using output_key

    **IMPORTANT:**
    - Just call the tool and return the raw result
    - Do NOT format or modify the response
    - The next agent will handle formatting
    - You CANNOT upload or delete documents - only administrators can do that via the Knowledge Base page
    """,
    tools=[search_knowledge_base, list_documents],
    output_key="raw_search_results",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit
)

# Formatter agent - formats the data into KnowledgeBaseOutput schema
knowledge_base_formatter = LlmAgent(
    name="knowledge_base_formatter",
    model="gemini-2.5-flash",
    description="Formats knowledge base search results into structured output",
    instruction="""
    You format search results into the KnowledgeBaseOutput schema.

    **INPUT:**
    You receive raw_search_results from the previous agent with:
    - answer: the main answer text
    - citations: array of {source: "filename", content: "snippet text"}

    **YOUR JOB:**
    Format into KnowledgeBaseOutput with:
    - operation: "search"
    - success: true
    - message: "Search completed successfully"
    - answer: the answer from raw_search_results
    - citations: COPY the citations array EXACTLY (preserve both source and content)
    - suggested_questions: Generate 3-5 relevant follow-up questions

    **CRITICAL - CITATION HANDLING:**
    - Preserve BOTH "source" and "content" fields from each citation
    - DO NOT modify or summarize the citation content
    - DO NOT drop any fields
    - Copy the citations array exactly as provided

    **RULES:**
    - Return valid JSON matching KnowledgeBaseOutput schema
    - Include all citations with full content
    - Generate helpful follow-up questions
    - Keep language clear and professional
    """,
    output_schema=KnowledgeBaseOutput,
    output_key="knowledge_base_output",
    before_model_callback=log_agent_entry,
    after_model_callback=log_agent_exit
)

# Sequential agent combining retriever and formatter
KnowledgeBaseAnalyst = SequentialAgent(
    name="KnowledgeBaseAnalyst",
    description="Manages and searches the college admissions knowledge base. Can upload documents, list documents, and search for expert insights and best practices.",
    sub_agents=[
        knowledge_base_retriever,
        knowledge_base_formatter
    ]
)
