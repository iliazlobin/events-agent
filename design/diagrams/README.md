# Events Agent - Architecture Diagrams

This directory contains system architecture diagrams for the Events Agent project.

## Excalidraw Diagrams (Interactive)

| Diagram | Description | Created | Editable Link |
|---------|-------------|---------|---------------|
| **High-Level Architecture v1** | 5-layer system architecture showing data flow from event sources through crawlers, processing, repository, to SQLite storage | 2026-02-13 | [Edit on Excalidraw](https://excalidraw.com/#json=5G02AGsw_HiK3Orz2dSYb,zSef7KaL1h-sQbAtSLRGQA) |

## PlantUML Diagrams (Static)

| File | Description |
|------|-------------|
| `01-system-architecture.puml` | High-level system architecture |
| `02-component-diagram.puml` | Component relationships and dependencies |
| `03-sequence-crawl-flow.puml` | Sequence diagram for crawl workflow |
| `04-deployment-diagram.puml` | Deployment architecture |
| `05-task-state-machine.puml` | Task state transitions |
| `06-data-flow.puml` | Data flow through the system |
| `07-class-diagram.puml` | Class diagram with relationships |

## How to Use

1. **View/Edit**: Click the "Edit on Excalidraw" link to open the diagram
2. **Export**: Click "Export image" in Excalidraw and download as PNG/SVG
3. **Save**: Place exported images in this `design/diagrams/` directory
4. **Embed**: Add to project documentation using markdown:
   ```markdown
   ![Architecture](design/diagrams/architecture-v1.png)
   [Edit diagram](https://excalidraw.com/#json=...)
   ```

## Diagram Checkpoints

- **architecture-v1**: `00111e603b894ecf9c`

These checkpoint IDs can be used to restore and continue editing diagrams programmatically.
