
import sys
import json
import glob
from pathlib import Path

# Set up path to import model.py
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

try:
    from model import UniversityProfile
except ImportError as e:
    print(f"CRITICAL: Could not import model.py: {e}")
    sys.exit(1)

research_dir = current_dir / "research"
files = sorted(list(research_dir.glob("*.json")))

print(f"\n🔍 Analyzing {len(files)} files in {research_dir}...\n")

headers = ["File", "Status", "Issues"]
rows = []

for f in files:
    fname = f.name
    try:
        data = json.loads(f.read_text())
        UniversityProfile.model_validate(data)
        rows.append([fname, "✅ PASS", ""])
    except json.JSONDecodeError:
         rows.append([fname, "❌ FAIL", "Invalid JSON format"])
    except Exception as e:
        # Pydantic validation error
        error_msg = str(e).split('\n')[0] # First line of error usually generic
        # Get detailed errors
        details = []
        if hasattr(e, 'errors'):
            for err in e.errors():
                loc = ".".join(str(l) for l in err['loc'])
                msg = err['msg']
                details.append(f"{loc}: {msg}")
        
        issue_summary = "; ".join(details[:3]) 
        if len(details) > 3:
            issue_summary += f" (+{len(details)-3} more)"
            
        rows.append([fname, "❌ FAIL", issue_summary])

# Print Table
col_widths = [max(len(r[0]) for r in rows) + 2, 8, max(len(r[2]) for r in rows) + 2]
header_row = "".join(word.ljust(width) for word, width in zip(headers, col_widths))
print("-" * len(header_row))
print(header_row)
print("-" * len(header_row))

for row in rows:
    print("".join(word.ljust(width) for word, width in zip(row, col_widths)))
