
import asyncio
import os
import logging
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# Import the agent
from agents.college_expert_hybrid.agent import MasterReasoningAgent

# Configure logging
logging.basicConfig(level=logging.INFO)

async def test_deep_research():
    print("\n\n=== TESTING DEEP RESEARCH ROUTING ===\n")
    
    # Query that SHOULD trigger DeepResearchAgent
    query = "What is the specific research focus of the BAIR lab at UC Berkeley and who are the key professors?"
    # query = "What is the student vibe at UCLA?" 
    
    print(f"User Query: {query}")
    
    session_service = InMemorySessionService()
    runner = Runner(agent=MasterReasoningAgent, session_service=session_service, app_name="test_app")
    await session_service.create_session(app_name="test_app", user_id="test_user", session_id="test_session")
    
    content = types.Content(role="user", parts=[types.Part(text=query)])
    
    print("\n--- Running Agent ---")
    async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=content):
        # Debug event
        print(f"\n[EVENT]: {event.model_dump_json(exclude_none=True)}")
        
        if hasattr(event, 'author') and event.author == "DeepResearchAgent":
            print(f"\n[DeepResearchAgent] invoked!")
        
        if event.is_final_response():
            print(f"\n[FINAL RESPONSE]:\n{event.content.parts[0].text}")

if __name__ == "__main__":
    asyncio.run(test_deep_research())
