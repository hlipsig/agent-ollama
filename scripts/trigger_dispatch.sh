#!/usr/bin/env bash
set -euo pipefail

# Trigger a repository_dispatch event for this repo.
# Requires either GITHUB_TOKEN (recommended from Actions) or a personal token
# with `repo` scope set in env var PERSONAL_TOKEN.

OWNER="hlipsig"
REPO="agent-ollama"
EVENT_TYPE="run-ollama-agent"

PAYLOAD="{\"triggered_by\": \"local-script\"}"

if command -v gh >/dev/null 2>&1; then
  echo "Using gh CLI to trigger repository_dispatch..."
  gh api --method POST \
    /repos/${OWNER}/${REPO}/dispatches \
    -f event_type=${EVENT_TYPE} \
    -f client_payload=${PAYLOAD}
  exit 0
fi

if [ -n "${GITHUB_TOKEN-}" ]; then
  TOKEN="$GITHUB_TOKEN"
elif [ -n "${PERSONAL_TOKEN-}" ]; then
  TOKEN="$PERSONAL_TOKEN"
else
  echo "Error: set GITHUB_TOKEN or PERSONAL_TOKEN in your environment." >&2
  exit 2
fi

API_URL="https://api.github.com/repos/${OWNER}/${REPO}/dispatches"

curl -sS -X POST "$API_URL" \
  -H "Authorization: token $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -d "{ \"event_type\": \"${EVENT_TYPE}\", \"client_payload\": ${PAYLOAD} }"

echo
