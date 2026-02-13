---
name: excalidraw-export
description: Export Excalidraw diagrams to excalidraw.com and return shareable URLs. Use after creating diagrams or when user requests a shareable link.
---

# Excalidraw Diagram Export

Export diagrams created with the Excalidraw MCP server to excalidraw.com and get shareable URLs.

## When to Use

Apply this skill when:
- User asks for a "shareable link" or "URL" after creating a diagram
- User wants to "export the diagram" or "share this diagram"
- You've created a diagram and want to provide a permanent link
- User wants to edit the diagram on excalidraw.com
- **Proactively after creating architecture diagrams** - Always export system design diagrams for documentation

## Diagram Documentation Workflow

After creating diagrams of system architecture, data flow, or component relationships:

1. **Export to URL** using this skill
2. **Instruct user to download** as PNG/SVG from the excalidraw.com URL
3. **Save to `docs/diagrams/`** directory with descriptive name
4. **Update `docs/diagrams/README.md`** table with new entry
5. **Embed in project README** with both image and editable link

Example instruction to user:
```
Diagram exported! Next steps:
1. Open: https://excalidraw.com/#json=abc123,def456
2. Click "Export image" → Download PNG
3. Save as: docs/diagrams/architecture.png
4. Update README.md:
   ![Architecture](docs/diagrams/architecture.png)
   [Edit diagram](https://excalidraw.com/#json=abc123,def456)
```

## Prerequisites

The Excalidraw MCP server must be configured in `.mcp.json`:

```json
{
  "mcpServers": {
    "excalidraw": {
      "command": "node",
      "args": [
        "/Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js",
        "--stdio"
      ]
    }
  }
}
```

## Export Process

### Method 1: From Checkpoint ID (Preferred)

When the diagram has been created with `create_view`, you'll have a checkpoint ID:

```bash
# Read the checkpoint data
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_checkpoint","arguments":{"id":"<CHECKPOINT_ID>"}}}' | node /Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js --stdio | tail -1
```

Then export with full Excalidraw JSON format:

```bash
# Export to excalidraw.com
cat <<'EOF' | node /Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js --stdio 2>/dev/null | tail -1 | jq -r '.result.content[0].text'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"export_to_excalidraw","arguments":{"json":"<FULL_EXCALIDRAW_JSON>"}}}
EOF
```

### Method 2: From Elements Array

If you have the elements array directly, wrap it in the Excalidraw format:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [<YOUR_ELEMENTS>],
  "appState": {
    "viewBackgroundColor": "#ffffff"
  }
}
```

Required fields for each element:
- Standard Excalidraw fields: `type`, `id`, `x`, `y`, `width`, `height`
- Additional: `strokeColor`, `strokeWidth`, `roughness`, `opacity`, `seed`, `version`, `versionNonce`, `isDeleted`, `boundElements`, `updated`, `link`, `locked`

## Helper Script

Create a helper function to simplify export:

```bash
#!/bin/bash
# Usage: export_diagram.sh <checkpoint_id>

CHECKPOINT_ID="$1"
SERVER_PATH="/Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js"

# Read checkpoint
checkpoint_data=$(cat <<EOF | node "$SERVER_PATH" --stdio 2>/dev/null | tail -1 | jq -r '.result.content[0].text'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_checkpoint","arguments":{"id":"$CHECKPOINT_ID"}}}
EOF
)

# Parse elements array
elements=$(echo "$checkpoint_data" | jq -c '.elements')

# Build full Excalidraw JSON
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
  }')

# Export to excalidraw.com
export_request=$(jq -n \
  --arg json "$full_json" \
  '{
    jsonrpc: "2.0",
    id: 2,
    method: "tools/call",
    params: {
      name: "export_to_excalidraw",
      arguments: {
        json: $json
      }
    }
  }')

# Get URL
cat <<EOF | node "$SERVER_PATH" --stdio 2>/dev/null | tail -1 | jq -r '.result.content[0].text'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
$export_request
EOF
```

## Example: Complete Export Flow

```bash
# 1. Get checkpoint data
checkpoint_id="1ab772c7b5da4416ae"

# 2. Read checkpoint
data=$(cat <<'EOF' | node /Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js --stdio 2>/dev/null | tail -1
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"read_checkpoint","arguments":{"id":"1ab772c7b5da4416ae"}}}
EOF
)

# 3. Extract elements and build full JSON
elements=$(echo "$data" | jq -r '.result.content[0].text' | jq -c '.elements')
full_json=$(jq -n --argjson els "$elements" '{type:"excalidraw",version:2,source:"https://excalidraw.com",elements:$els,appState:{viewBackgroundColor:"#ffffff"}}')

# 4. Export and get URL
echo "$full_json" | jq -Rs '{jsonrpc:"2.0",id:2,method:"tools/call",params:{name:"export_to_excalidraw",arguments:{json:.}}}' | \
  cat <(echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"export","version":"1.0"}}}') - | \
  node /Users/iliazlobin/Code/mcp-servers/excalidraw-mcp-app/dist/index.js --stdio 2>/dev/null | tail -1 | jq -r '.result.content[0].text'
```

## Output Format

Success:
```
https://excalidraw.com/#json=RrLQKHus_a2E4bAUZeVT8,OlOu5-9pUaf-q_e9o9SC-A
```

Error:
```
Export failed: <error message>
```

## Troubleshooting

**"Export data exceeds 5 MB limit"**:
- Diagram is too large. Simplify or split into multiple diagrams.

**"Upload failed: 500"**:
- excalidraw.com service may be down. Try again later.

**"read failed: checkpoint not found"**:
- Checkpoint ID is invalid or expired.
- Checkpoints are stored in `$TMPDIR/excalidraw-mcp-checkpoints/` (local) or Upstash Redis (production).

**Empty response**:
- Check that the server is running and MCP connection is established.
- Verify the JSON is valid Excalidraw format with all required fields.

## Alternative: UI Export Button

When viewing a diagram in Claude Desktop or an MCP client:
1. Diagram renders in the widget
2. Click "Export" button (top-right)
3. Confirm export dialog
4. URL opens in new browser tab

This skill is for programmatic/CLI export when you need the URL in the conversation response.

## Notes

- The `export_to_excalidraw` tool has `visibility: ["app"]` in the server code, meaning it's primarily designed for widget UI calls
- However, it works via direct JSON-RPC stdio calls as shown above
- The export creates an encrypted, compressed payload uploaded to excalidraw.com
- URLs are permanent and shareable
- Diagrams exported to excalidraw.com can be edited there and re-exported
