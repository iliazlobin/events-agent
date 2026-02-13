#!/bin/bash
# Export Excalidraw diagram from checkpoint ID to excalidraw.com
# Usage: ./export_diagram.sh <checkpoint_id>

set -euo pipefail

CHECKPOINT_ID="${1:-}"
SERVER_PATH="/Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js"

if [ -z "$CHECKPOINT_ID" ]; then
  echo "Usage: $0 <checkpoint_id>" >&2
  exit 1
fi

if [ ! -f "$SERVER_PATH" ]; then
  echo "Error: Excalidraw server not found at $SERVER_PATH" >&2
  exit 1
fi

echo "Reading checkpoint: $CHECKPOINT_ID" >&2

# Step 1: Read checkpoint data
checkpoint_response=$(cat <<EOF | node "$SERVER_PATH" --stdio 2>/dev/null
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_checkpoint","arguments":{"id":"$CHECKPOINT_ID"}}}
EOF
)

checkpoint_data=$(echo "$checkpoint_response" | tail -1 | jq -r '.result.content[0].text')

if [ -z "$checkpoint_data" ] || [ "$checkpoint_data" = "null" ]; then
  echo "Error: Failed to read checkpoint $CHECKPOINT_ID" >&2
  exit 1
fi

# Step 2: Parse checkpoint and add required fields for each element
elements=$(echo "$checkpoint_data" | jq -c '.elements | map(. + {
  strokeColor: (.strokeColor // "#1e1e1e"),
  backgroundColor: (.backgroundColor // "transparent"),
  fillStyle: (.fillStyle // "solid"),
  strokeWidth: (.strokeWidth // 2),
  roughness: (.roughness // 1),
  opacity: (.opacity // 100),
  seed: (.seed // 1),
  version: (.version // 1),
  versionNonce: (.versionNonce // 1),
  isDeleted: (.isDeleted // false),
  boundElements: (.boundElements // null),
  updated: (.updated // 1),
  link: (.link // null),
  locked: (.locked // false)
})')

# Step 3: Build full Excalidraw JSON format
full_json=$(jq -n \
  --argjson els "$elements" \
  '{
    type: "excalidraw",
    version: 2,
    source: "https://excalidraw.com",
    elements: $els,
    appState: {
      viewBackgroundColor: "#ffffff"
    }
  }' | jq -c)

echo "Uploading to excalidraw.com..." >&2

# Step 4: Export to excalidraw.com
export_response=$(cat <<EOF | node "$SERVER_PATH" --stdio 2>/dev/null
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"export_to_excalidraw","arguments":{"json":$(echo "$full_json" | jq -Rs .)}}}
EOF
)

# Step 5: Extract and return URL
url=$(echo "$export_response" | tail -1 | jq -r '.result.content[0].text')

if [[ "$url" == https://excalidraw.com/* ]]; then
  echo "✓ Export successful!" >&2
  echo "$url"
else
  echo "Error: Export failed - $url" >&2
  exit 1
fi
