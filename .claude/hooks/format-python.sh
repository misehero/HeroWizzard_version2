#!/bin/bash
# PostToolUse hook: auto-format Python files after Write/Edit
# Reads tool_input.file_path from stdin JSON, runs black + isort if .py file

FILE=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null)

if [[ "$FILE" == *.py ]] && [[ -f "$FILE" ]]; then
    python -m black "$FILE" --quiet 2>/dev/null
    python -m isort "$FILE" --quiet 2>/dev/null
fi
exit 0
