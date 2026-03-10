import sys
import json
import os
from datetime import datetime

with open(".gemini/hooks/debug_stdin.log", "a") as f:
    f.write(f"\n--- {datetime.now().isoformat()} ---\n")
    if not sys.stdin.isatty():
        content = sys.stdin.read()
        f.write(content)
    else:
        f.write("No stdin (isatty)\n")

print(json.dumps({"decision": "allow"}))
