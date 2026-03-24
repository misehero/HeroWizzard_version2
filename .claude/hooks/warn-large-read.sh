#!/bin/bash
# PreToolUse hook: warn when reading files over 500 lines (token awareness)
# Exit 0 = allow (warning only, does not block)

FILE=$(python -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path', d.get('tool_input',{}).get('path','')))" 2>/dev/null)

if [[ -f "$FILE" ]]; then
    LINES=$(wc -l < "$FILE" 2>/dev/null | tr -d ' ')
    if [[ "$LINES" -gt 500 ]] 2>/dev/null; then
        echo "WARNING: $FILE has $LINES lines. Consider reading specific line ranges to save tokens." >&2
    fi
fi
exit 0
