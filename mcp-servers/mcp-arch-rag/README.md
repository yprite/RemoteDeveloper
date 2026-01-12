# mcp-arch-rag

MCP RAG Server for Software Architecture Patterns.

## Knowledge Sources

- **Clean Architecture** - Robert C. Martin
- **DDD** - Domain-Driven Design
- **Event-Driven** - Event sourcing, CQRS, Outbox
- **Saga** - Distributed transactions
- **AWS Well-Architected** - Cloud best practices
- **Microservices** - Decomposition, communication, reliability
- **Distributed Systems** - CAP, consistency, patterns

## Usage

```python
from mcp-arch-rag.server import create_server

server = create_server()
results = server.query("saga distributed transaction", top_k=5)
```
