"""
Markdown Report Generator for LLM-as-Judge Evaluation Results.

Generates comprehensive markdown reports with full responses and conversation details.
"""
import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from ..core import EvalResult


def generate_markdown_report(
    results: List[EvalResult],
    category: str = "all",
    output_dir: str = None,
    conversation_details: List[Dict[str, Any]] = None
) -> str:
    """Generate a comprehensive markdown report for test results."""
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "reports"
    else:
        output_dir = Path(output_dir)
    
    output_dir.mkdir(exist_ok=True)
    
    # Calculate stats
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    avg_score = sum(r.score for r in results) / len(results) if results else 0
    pass_rate = (passed / len(results) * 100) if results else 0
    
    # Group by category
    by_category = {}
    for r in results:
        if r.category not in by_category:
            by_category[r.category] = []
        by_category[r.category].append(r)
    
    # Generate markdown
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_name = f"report_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    lines = [
        f"# 📊 Evaluation Report: {category.title()}",
        "",
        f"> **Generated**: {timestamp}  ",
        f"> **Agent**: college_expert_hybrid",
        "",
        "---",
        "",
        "## 📈 Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| **Total Tests** | {len(results)} |",
        f"| **Passed** | ✅ {passed} |",
        f"| **Failed** | ❌ {failed} |",
        f"| **Pass Rate** | {pass_rate:.1f}% |",
        f"| **Average Score** | {avg_score:.2f} |",
        "",
    ]
    
    # Category breakdown
    if len(by_category) > 1:
        lines.extend([
            "## 📋 Results by Category",
            "",
            "| Category | Passed | Total | Rate | Status |",
            "|----------|--------|-------|------|--------|",
        ])
        for cat, cat_results in sorted(by_category.items()):
            cat_passed = sum(1 for r in cat_results if r.passed)
            cat_rate = (cat_passed / len(cat_results) * 100) if cat_results else 0
            status = "✅ Pass" if cat_rate >= 80 else "⚠️ Partial" if cat_rate >= 50 else "❌ Fail"
            lines.append(f"| {cat} | {cat_passed} | {len(cat_results)} | {cat_rate:.0f}% | {status} |")
        lines.append("")
    
    # Quick summary table
    lines.extend([
        "## 📝 Quick Results",
        "",
        "| Status | Test ID | Score |",
        "|--------|---------|-------|",
    ])
    for r in results:
        status = "✅" if r.passed else "❌"
        lines.append(f"| {status} | `{r.eval_id}` | {r.score:.2f} |")
    lines.append("")
    
    # Detailed results with full responses
    lines.extend([
        "---",
        "",
        "## 📖 Detailed Test Results",
        "",
    ])
    
    for cat, cat_results in sorted(by_category.items()):
        # Skip multi-turn conversations (handled separately)
        if cat == "Multi-Turn Conversations":
            continue
            
        lines.extend([
            f"### 🏷️ {cat}",
            "",
        ])
        
        for r in cat_results:
            status_icon = "✅" if r.passed else "❌"
            lines.extend([
                f"#### {status_icon} `{r.eval_id}`",
                "",
                f"**Score**: {r.score:.2f} | **Status**: {'PASSED' if r.passed else 'FAILED'}",
                "",
            ])
            
            # Add query if available
            if hasattr(r, 'query') and r.query:
                lines.extend([
                    "**User Query**:",
                    f"> {r.query}",
                    "",
                ])
            
            # Add reasoning
            lines.extend([
                "**Judge Reasoning**:",
                f"> {r.reasoning}",
                "",
            ])
            
            # Add full response
            if hasattr(r, 'full_response') and r.full_response:
                response_text = r.full_response
            elif r.response_snippet:
                response_text = r.response_snippet
            else:
                response_text = "No response captured"
            
            # Clean up JSON formatting in response
            if response_text.startswith('{') and '"result"' in response_text:
                try:
                    parsed = json.loads(response_text)
                    if 'result' in parsed:
                        response_text = parsed['result']
                except:
                    pass
            
            lines.extend([
                "**Agent Response**:",
                "",
                "```",
                response_text,
                "```",
                "",
                "---",
                "",
            ])
    
    # Multi-turn conversation details
    if conversation_details:
        lines.extend([
            "## 💬 Multi-Turn Conversation Details",
            "",
        ])
        
        for conv in conversation_details:
            conv_id = conv.get('conv_id', 'unknown')
            description = conv.get('description', '')
            turns = conv.get('turns', [])
            overall_passed = conv.get('passed', False)
            overall_score = conv.get('score', 0.0)
            
            status_icon = "✅" if overall_passed else "❌"
            lines.extend([
                f"### {status_icon} `{conv_id}`",
                "",
                f"**Description**: {description}  ",
                f"**Overall Score**: {overall_score:.2f} | **Status**: {'PASSED' if overall_passed else 'FAILED'}",
                "",
                "#### Conversation Flow",
                "",
            ])
            
            for i, turn in enumerate(turns):
                turn_num = i + 1
                user_msg = turn.get('user_message', '')
                agent_response = turn.get('agent_response', '')
                turn_passed = turn.get('passed', False)
                turn_score = turn.get('score', 0.0)
                turn_reasoning = turn.get('reasoning', '')
                context_maintained = turn.get('context_maintained', True)
                
                turn_icon = "✅" if turn_passed else "❌"
                context_icon = "🔗" if context_maintained else "⚠️"
                
                # Clean up JSON in response
                if agent_response.startswith('{') and '"result"' in agent_response:
                    try:
                        parsed = json.loads(agent_response)
                        if 'result' in parsed:
                            agent_response = parsed['result']
                    except:
                        pass
                
                lines.extend([
                    f"**Turn {turn_num}** {turn_icon} (Score: {turn_score:.2f}) {context_icon}",
                    "",
                    f"👤 **User**: {user_msg}",
                    "",
                    f"🤖 **Agent**:",
                    "```",
                    agent_response,
                    "```",
                    "",
                    f"📋 **Judgment**: {turn_reasoning}",
                    "",
                ])
            
            lines.extend(["---", ""])
    
    # Multi-turn conversations from results (if no detailed conversation data)
    elif "Multi-Turn Conversations" in by_category:
        lines.extend([
            "## 💬 Multi-Turn Conversation Results",
            "",
        ])
        
        for r in by_category["Multi-Turn Conversations"]:
            status_icon = "✅" if r.passed else "❌"
            lines.extend([
                f"### {status_icon} `{r.eval_id}`",
                "",
                f"**Score**: {r.score:.2f} | **Status**: {'PASSED' if r.passed else 'FAILED'}",
                "",
                "**Judge Reasoning**:",
                f"> {r.reasoning}",
                "",
            ])
            
            # Show criteria met
            if r.criteria_met:
                lines.extend([
                    "**Turn Results**:",
                    "",
                    "| Turn | Passed |",
                    "|------|--------|",
                ])
                for turn_name, passed in r.criteria_met.items():
                    icon = "✅" if passed else "❌"
                    lines.append(f"| {turn_name} | {icon} |")
                lines.append("")
            
            lines.extend(["---", ""])
    
    # Write report
    report_content = "\n".join(lines)
    report_path = output_dir / report_name
    report_path.write_text(report_content)
    
    # Also write a latest.md for easy access
    latest_path = output_dir / f"latest_{category}.md"
    latest_path.write_text(report_content)
    
    return str(report_path)


def print_summary(results: List[EvalResult]) -> None:
    """Print a quick summary to console."""
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    avg_score = sum(r.score for r in results) / total if total > 0 else 0
    
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Passed: {passed}/{total} ({100*passed/total:.0f}%)")
    print(f"  Average Score: {avg_score:.2f}")
    print("=" * 60)
