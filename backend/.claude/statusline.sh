#!/usr/bin/env bash
# Opt-in statusline for interactive Claude Code sessions in this repo.
#
# CC pipes a rich JSON session object on stdin; we render a one-liner and, when
# BITCH_STEWIE_RUN_ID is set (exported before launching `claude`), append live
# delegation-run telemetry from the assistant backend.
#
# Enable in .claude/settings.json:
#   { "statusLine": { "type": "command", "command": ".claude/statusline.sh" } }

input=$(cat)

model=$(printf '%s' "$input" | jq -r '.model.display_name // "?"')
cwd=$(printf '%s' "$input" | jq -r '.workspace.current_dir // "?" | split("/")[-1]')
cost=$(printf '%s' "$input" | jq -r '.cost.total_cost_usd // empty')

line="[$model] $cwd"
[ -n "$cost" ] && line="$line \$${cost}"

api="${ASSISTANT_API:-http://127.0.0.1:8011}"
if [ -n "$BITCH_STEWIE_RUN_ID" ]; then
  run=$(curl -sf --max-time 1 "$api/api/runs/$BITCH_STEWIE_RUN_ID/statusline" 2>/dev/null)
  if [ -n "$run" ]; then
    status=$(printf '%s' "$run" | jq -r '.status')
    tools=$(printf '%s' "$run" | jq -r '.events.post_tool')
    verdict=$(printf '%s' "$run" | jq -r '.review_verdict // "-"')
    line="$line | run:$status tools:$tools review:$verdict"
  fi
fi

printf '%s' "$line"