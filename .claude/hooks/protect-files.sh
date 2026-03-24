#!/bin/bash
# PreToolUse hook: block edits to protected files
# Exit 2 = block action, stderr message shown to Claude

FILE=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path', d.get('tool_input',{}).get('path','')))" 2>/dev/null)

# Skip if no file path extracted
[[ -z "$FILE" ]] && exit 0

# Protected patterns
PROTECTED=(
    "config/settings.py"
    "deploy/deploy.sh"
    ".github/workflows/"
    ".deploy_key"
    ".env"
)

for pattern in "${PROTECTED[@]}"; do
    if echo "$FILE" | grep -q "$pattern"; then
        echo "BLOCKED: $FILE is a protected file. Ask for explicit permission before modifying." >&2
        exit 2
    fi
done

# Block editing applied migrations
if echo "$FILE" | grep -qE "apps/.*/migrations/0[0-9]+_.*\.py$"; then
    echo "BLOCKED: $FILE is an applied migration. Never modify applied migrations." >&2
    exit 2
fi

exit 0
