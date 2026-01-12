# mcp-ux-rag

MCP RAG Server for UX/UI Design Patterns.

## Knowledge Sources

- **Shadcn/ui** - Component library patterns
- **Tailwind CSS** - Utility-first styling
- **Radix UI** - Accessible primitives
- **Material Design** - Google's design system
- **NNG (Nielsen Norman Group)** - UX research principles
- **Apple HIG** - Human Interface Guidelines

## Usage

```python
from mcp-ux-rag.server import create_server

server = create_server()
results = server.query("button accessibility", top_k=5)
```
