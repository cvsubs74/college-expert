#!/usr/bin/env python3
"""
Generate prompt-specific brainstorming questions using LLM.
These get persisted with each essay prompt for instant loading.
"""
import json
import os
import requests
from pathlib import Path
import google.generativeai as genai

RESEARCH_DIR = Path("agents/university_profile_collector/research")
KB_URL = "https://knowledge-base-manager-universities-pfnwjfp26a-ue.a.run.app"

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")


def generate_brainstorming_questions(prompt_text: str, university_name: str) -> list[str]:
    """Use LLM to generate 5 specific brainstorming questions for this exact prompt."""
    
    system_prompt = f"""You are a college essay brainstorming coach. Your job is to generate 5 thoughtful questions that will help a student discover their unique story for this specific essay prompt.

RULES:
1. Questions should be SPECIFIC to this exact prompt, not generic
2. Guide the student to self-reflection, don't give answers
3. Help them find authentic, personal stories
4. Questions should be conversational and encouraging
5. Each question should unlock a different angle or memory

ESSAY PROMPT: "{prompt_text}"
UNIVERSITY: {university_name}

Generate exactly 5 brainstorming questions. Return ONLY a JSON array of 5 strings, no explanation.
Example: ["Question 1?", "Question 2?", "Question 3?", "Question 4?", "Question 5?"]"""

    try:
        response = model.generate_content(system_prompt)
        text = response.text.strip()
        
        # Clean up markdown if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()
        
        questions = json.loads(text)
        if isinstance(questions, list) and len(questions) >= 5:
            return questions[:5]
        return []
    except Exception as e:
        print(f"    ⚠️ LLM error: {e}")
        return []


def update_university_with_questions(filepath: Path) -> tuple[int, int]:
    """Update all essay prompts in a university JSON with brainstorming questions."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        university_name = data.get('metadata', {}).get('official_name', filepath.stem.replace('_', ' ').title())
        prompts = data.get('application_process', {}).get('essay_prompts', [])
        
        if not prompts:
            return 0, 0
        
        updated = 0
        for i, prompt in enumerate(prompts):
            # Skip if already has questions
            if prompt.get('brainstorming_questions') and len(prompt['brainstorming_questions']) >= 5:
                continue
            
            prompt_text = prompt.get('prompt', '')
            if not prompt_text:
                continue
            
            print(f"    Generating for prompt {i+1}: {prompt_text[:60]}...")
            questions = generate_brainstorming_questions(prompt_text, university_name)
            
            if questions:
                prompt['brainstorming_questions'] = questions
                updated += 1
        
        # Save back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return len(prompts), updated
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return 0, 0


def ingest_university(filepath: Path) -> bool:
    """Ingest university to knowledge base."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            profile = json.load(f)
        response = requests.post(KB_URL, json={"profile": profile}, headers={"Content-Type": "application/json"}, timeout=300)
        return response.ok and response.json().get('success', False)
    except:
        return False


def main():
    # Find all universities with essay prompts
    universities_with_prompts = []
    
    for filepath in RESEARCH_DIR.glob("*.json"):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            prompts = data.get('application_process', {}).get('essay_prompts', [])
            if prompts:
                # Check if any prompt needs questions
                needs_questions = any(not p.get('brainstorming_questions') for p in prompts)
                if needs_questions:
                    universities_with_prompts.append(filepath)
        except:
            continue
    
    print(f"Found {len(universities_with_prompts)} universities needing brainstorming questions\n")
    
    total_prompts = 0
    total_updated = 0
    
    for filepath in universities_with_prompts:
        print(f"📝 {filepath.stem}")
        prompts_count, updated_count = update_university_with_questions(filepath)
        total_prompts += prompts_count
        total_updated += updated_count
        
        if updated_count > 0:
            if ingest_university(filepath):
                print(f"   ✅ Ingested ({updated_count}/{prompts_count} prompts updated)")
            else:
                print(f"   ❌ Ingest failed")
        else:
            print(f"   ⏭️ Already complete")
    
    print(f"\n📊 Summary: {total_updated}/{total_prompts} prompts updated with brainstorming questions")


if __name__ == "__main__":
    main()
