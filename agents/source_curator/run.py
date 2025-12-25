#!/usr/bin/env python3
"""
Run Source Curator Agent - CLI for discovering and curating university data sources.

Usage:
    python run.py "University of Southern California"
    python run.py "USC" --verbose
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

# Add parent path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from parent agent's .env
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / "university_profile_collector" / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded API key from: {env_path}")

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from agent import root_agent


def setup_logging(verbose: bool = False):
    """Configure logging for the agent."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    # Reduce noise from httpx
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


async def run_discovery(university_name: str, verbose: bool = False):
    """
    Run the source curator agent to discover sources for a university.
    
    Args:
        university_name: Name or abbreviation of the university
        verbose: Whether to enable debug logging
    """
    setup_logging(verbose)
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("🔍 Source Curator Agent")
    print("=" * 60)
    print(f"University: {university_name}")
    print("-" * 60)
    
    # Create session service
    session_service = InMemorySessionService()
    
    # Create runner
    runner = Runner(
        agent=root_agent,
        app_name="source_curator",
        session_service=session_service
    )
    
    # Create session with initial state
    session = await session_service.create_session(
        app_name="source_curator",
        user_id="cli_user",
        state={
            "university_name": university_name,
            "university_id": university_name.lower().replace(" ", "_").replace(",", "")
        }
    )
    
    # Create proper message content
    query = f"Find and curate sources for: {university_name}"
    message_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=query)]
    )
    
    logger.info(f"Starting discovery for: {university_name}")
    
    try:
        async for event in runner.run_async(
            user_id="cli_user",
            session_id=session.id,
            new_message=message_content
        ):
            # Print agent responses
            if hasattr(event, 'text') and event.text:
                print(f"\n{event.text}")
            elif hasattr(event, 'content') and event.content:
                content = event.content
                if isinstance(content, dict):
                    # Check for final results
                    if 'yaml_output_path' in content:
                        print(f"\n✅ YAML config saved: {content['yaml_output_path']}")
                    elif 'discovered_sources' in content:
                        sources = content['discovered_sources']
                        print(f"\n📋 Discovered {len(sources)} sources")
    except Exception as e:
        logger.error(f"Error during discovery: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ Source discovery complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Review the generated YAML file in sources/universities/")
    print("2. Validate each URL is correct and accessible")
    print("3. Update extraction_config with correct selectors")
    print("4. Set is_active: true for validated sources")
    print("5. Commit to Git")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Source Curator Agent - Discover and curate university data sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run.py "University of Southern California"
    python run.py "USC" --verbose
    python run.py "Stanford University"
        """
    )
    
    parser.add_argument(
        "university",
        help="Name or abbreviation of the university to research"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging"
    )
    
    args = parser.parse_args()
    
    # Run the async discovery
    exit_code = asyncio.run(run_discovery(args.university, args.verbose))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
