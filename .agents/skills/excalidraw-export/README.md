# Excalidraw Export Skill

Export Excalidraw diagrams to shareable excalidraw.com URLs.

## Quick Start

```bash
# Export a diagram from checkpoint ID
./export_diagram.sh <checkpoint_id>

# Example
./export_diagram.sh 1ab772c7b5da4416ae
# Output: https://excalidraw.com/#json=...
```

## Usage Scenarios

### 1. After Creating a Diagram

When an AI creates a diagram using the excalidraw MCP server:

```
User: "Draw a system architecture diagram"
AI: Creates diagram → checkpoint ID: abc123def456
User: "Export this diagram"
AI: Runs: ./export_diagram.sh abc123def456
    Returns: https://excalidraw.com/#json=...
```

### 2. From events-agent Code

```python
import subprocess

def export_diagram(checkpoint_id: str) -> str:
    """Export an Excalidraw diagram to excalidraw.com."""
    script = ".agents/skills/excalidraw-export/export_diagram.sh"
    result = subprocess.run(
        [script, checkpoint_id],
        capture_output=True,
        text=True,
        check=True
    )
    # Last line is the URL
    return result.stdout.strip().split('\n')[-1]

# Usage
url = export_diagram("1ab772c7b5da4416ae")
print(f"Diagram: {url}")
```

### 3. Bulk Export

```bash
# Export all checkpoints in temp directory
for checkpoint in $TMPDIR/excalidraw-mcp-checkpoints/*.json; do
  id=$(basename "$checkpoint" .json)
  echo "Exporting $id..."
  ./export_diagram.sh "$id" || echo "Failed: $id"
done
```

## How It Works

1. **Read checkpoint** via `read_checkpoint` MCP tool
2. **Normalize elements** - add required Excalidraw fields
3. **Build full JSON** with proper format structure
4. **Upload to excalidraw.com** via `export_to_excalidraw` tool
5. **Return shareable URL** with encryption key

## Output

```bash
$ ./export_diagram.sh 1ab772c7b5da4416ae
Reading checkpoint: 1ab772c7b5da4416ae
Uploading to excalidraw.com...
✓ Export successful!
https://excalidraw.com/#json=-R7qmG0pff9tXr035nOV9,u5oJNaAg4xL83u2cmW_0mg
```

The URL:
- Is permanent and shareable
- Contains encrypted diagram data
- Can be edited on excalidraw.com
- Works in any browser

## Requirements

- Excalidraw MCP server built and available
- `jq` installed for JSON processing
- Node.js to run the MCP server

## Troubleshooting

**"checkpoint not found"**:
- Check `$TMPDIR/excalidraw-mcp-checkpoints/` for available checkpoint files
- Checkpoints may expire or be cleared

**"Upload failed"**:
- Network issue or excalidraw.com service down
- Check diagram size (max 5MB)

**"Export data exceeds limit"**:
- Diagram is too large
- Simplify or split into multiple diagrams

## Integration with Claude Desktop

To use this in conversations:

```json
// ~/.mcp.json or claude_desktop_config.json
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

Then in conversation:
- "Draw a system diagram" → AI creates diagram with checkpoint ID
- "Export this" → AI runs export script and returns URL
