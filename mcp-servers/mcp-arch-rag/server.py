"""
MCP Architecture RAG Server - RAG service for software architecture patterns.

Provides architecture knowledge from:
- Clean Architecture
- Domain-Driven Design (DDD)
- Event-driven patterns
- Saga / CQRS / Outbox
- AWS Well-Architected Framework
- Microservices patterns
- Distributed system patterns

Also integrates with repo-specific RAG for context.
"""
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("mcp-arch-rag")

# Add backend to path for rag_service import
BACKEND_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "backend")
)
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

# Architecture pattern knowledge base
ARCH_PATTERNS = {
    "clean_architecture": {
        "description": "Clean Architecture by Robert C. Martin",
        "layers": [
            "Entities - Enterprise business rules",
            "Use Cases - Application business rules",
            "Interface Adapters - Controllers, Presenters, Gateways",
            "Frameworks & Drivers - Web, DB, External interfaces"
        ],
        "principles": [
            "Dependency Rule: Dependencies point inward",
            "Entities don't know about use cases",
            "Use cases don't know about adapters",
            "Business rules isolated from frameworks",
            "Testable without external systems"
        ],
        "directory_structure": {
            "domain/": "Entities, Value Objects, Domain Services",
            "application/": "Use Cases, DTOs, Interfaces",
            "infrastructure/": "Repositories, External Services",
            "presentation/": "Controllers, Views, API"
        }
    },
    "ddd": {
        "description": "Domain-Driven Design tactical patterns",
        "building_blocks": {
            "Entity": "Has identity, mutable state",
            "Value Object": "No identity, immutable, equality by value",
            "Aggregate": "Cluster of entities with root, transactional boundary",
            "Aggregate Root": "Entry point to aggregate, ensures invariants",
            "Domain Service": "Stateless operations across entities",
            "Repository": "Collection-like interface for aggregates",
            "Factory": "Complex object creation"
        },
        "strategic_patterns": [
            "Bounded Context - linguistic boundary",
            "Ubiquitous Language - shared vocabulary",
            "Context Map - relationships between contexts",
            "Anti-Corruption Layer - translation between contexts"
        ],
        "principles": [
            "Focus on core domain",
            "Model should reflect business language",
            "Bounded contexts for team autonomy",
            "Aggregates for consistency boundaries"
        ]
    },
    "event_driven": {
        "description": "Event-driven architecture patterns",
        "patterns": {
            "Event Sourcing": "Store state as sequence of events",
            "Event Notification": "Publish events for others to react",
            "Event-Carried State Transfer": "Events contain full state",
            "Domain Events": "Events within bounded context",
            "Integration Events": "Events across bounded contexts"
        },
        "messaging": [
            "Message Queue (point-to-point)",
            "Publish/Subscribe (fan-out)",
            "Event Bus / Message Broker",
            "Dead Letter Queue for failures"
        ],
        "considerations": [
            "Eventual consistency",
            "Idempotency for message handling",
            "Ordering guarantees",
            "At-least-once vs at-most-once delivery"
        ]
    },
    "saga_cqrs_outbox": {
        "description": "Distributed transaction patterns",
        "saga": {
            "purpose": "Long-running transactions across services",
            "choreography": "Each service publishes events, others react",
            "orchestration": "Central coordinator manages steps",
            "compensation": "Undo actions on failure"
        },
        "cqrs": {
            "purpose": "Separate read and write models",
            "command_side": "Handles writes, enforces invariants",
            "query_side": "Optimized for reads, denormalized",
            "sync": "Events propagate changes to read model"
        },
        "outbox": {
            "purpose": "Reliable event publishing with DB transactions",
            "pattern": "Write event to outbox table in same transaction",
            "publisher": "Background process reads and publishes",
            "benefits": "Atomicity, no distributed transaction needed"
        }
    },
    "aws_well_architected": {
        "description": "AWS Well-Architected Framework pillars",
        "pillars": {
            "Operational Excellence": [
                "Infrastructure as Code",
                "Frequent, small, reversible changes",
                "Anticipate failure",
                "Learn from operational failures"
            ],
            "Security": [
                "Strong identity foundation",
                "Traceability",
                "Security at all layers",
                "Protect data in transit and at rest",
                "Least privilege access"
            ],
            "Reliability": [
                "Automatic failure recovery",
                "Test recovery procedures",
                "Scale horizontally",
                "Stop guessing capacity"
            ],
            "Performance Efficiency": [
                "Use serverless architectures",
                "Go global in minutes",
                "Experiment more often"
            ],
            "Cost Optimization": [
                "Pay only for what you use",
                "Measure overall efficiency",
                "Analyze and attribute expenditure"
            ],
            "Sustainability": [
                "Understand your impact",
                "Maximize utilization",
                "Use managed services"
            ]
        }
    },
    "microservices": {
        "description": "Microservices architecture patterns",
        "decomposition": [
            "Decompose by business capability",
            "Decompose by subdomain (DDD)",
            "Self-contained service pattern",
            "Service per team"
        ],
        "communication": {
            "synchronous": "REST, gRPC, GraphQL",
            "asynchronous": "Message queues, Event streaming",
            "service_mesh": "Istio, Linkerd for traffic management"
        },
        "data_patterns": [
            "Database per service",
            "Shared database (anti-pattern usually)",
            "Saga for distributed transactions",
            "API Composition for queries"
        ],
        "reliability": [
            "Circuit Breaker",
            "Retry with exponential backoff",
            "Bulkhead isolation",
            "Timeout handling",
            "Health checks"
        ],
        "observability": [
            "Distributed tracing (Jaeger, Zipkin)",
            "Centralized logging (ELK, Loki)",
            "Metrics (Prometheus, Grafana)",
            "Correlation IDs"
        ]
    },
    "distributed_systems": {
        "description": "Distributed system fundamentals",
        "cap_theorem": {
            "C": "Consistency - all nodes see same data",
            "A": "Availability - every request gets response",
            "P": "Partition tolerance - system works despite network issues",
            "trade_off": "Can only guarantee 2 of 3 during partition"
        },
        "consistency_models": [
            "Strong consistency",
            "Eventual consistency",
            "Causal consistency",
            "Read-your-writes consistency"
        ],
        "patterns": {
            "Leader Election": "Raft, Paxos algorithms",
            "Sharding": "Horizontal data partitioning",
            "Replication": "Primary-replica, multi-master",
            "Load Balancing": "Round-robin, least-connections",
            "Rate Limiting": "Token bucket, sliding window"
        }
    }
}


class ArchRagServer:
    """MCP-compatible RAG server for architecture patterns + repo context."""
    
    def __init__(self, docs_path: Optional[str] = None):
        self.docs_path = docs_path or os.path.join(os.path.dirname(__file__), "docs")
        self.patterns = ARCH_PATTERNS
        self._rag_service = None
        logger.info("Architecture RAG Server initialized")
    
    def _get_rag_service(self):
        """Lazy load rag_service."""
        if self._rag_service is None:
            try:
                from core.rag_service import get_rag_service
                self._rag_service = get_rag_service()
            except Exception as e:
                logger.warning(f"Could not load rag_service: {e}")
        return self._rag_service
    
    def query(self, query: str, top_k: int = 5, repo_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query for architecture patterns + repo context.
        
        Combines:
        1. Pattern knowledge (Clean Arch, DDD, etc.)
        2. Repo-specific code from rag_service
        """
        query_lower = query.lower()
        results = []
        
        # 1. Query pattern knowledge
        for category, data in self.patterns.items():
            score = 0
            
            category_words = category.replace("_", " ").split()
            for word in category_words:
                if word in query_lower:
                    score += 10
            
            if any(word in data.get("description", "").lower() for word in query_lower.split()):
                score += 5
            
            def search_nested(obj, depth=0):
                nonlocal score
                if depth > 3:
                    return
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if any(word in k.lower() for word in query_lower.split() if len(word) > 3):
                            score += 3
                        search_nested(v, depth + 1)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, str):
                            if any(word in item.lower() for word in query_lower.split() if len(word) > 3):
                                score += 2
                        else:
                            search_nested(item, depth + 1)
            
            search_nested(data)
            
            if score > 0:
                results.append({
                    "category": category,
                    "score": score,
                    "content": json.dumps(data, ensure_ascii=False, indent=2),
                    "metadata": {"type": "arch_pattern", "source": category}
                })
        
        # 2. Query repo-specific code (if repo_filter provided)
        rag = self._get_rag_service()
        if rag and repo_filter:
            try:
                # Search for architecture-related code in the repo
                arch_query = f"architecture structure {query}"
                repo_results = rag.query(arch_query, top_k=top_k, repo_filter=repo_filter)
                
                for r in repo_results:
                    results.append({
                        "category": "repo_code",
                        "score": 8,  # High priority for actual repo code
                        "content": r.get("content", ""),
                        "metadata": {
                            "type": "repo_code",
                            "source": r.get("metadata", {}).get("file", "unknown"),
                            "repo": repo_filter
                        }
                    })
            except Exception as e:
                logger.warning(f"Repo RAG query failed: {e}")
        
        # Sort by score and return top_k
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
    
    def get_pattern(self, category: str) -> Optional[Dict[str, Any]]:
        """Get a specific pattern category."""
        return self.patterns.get(category)
    
    def get_all_patterns(self) -> Dict[str, Any]:
        """Get all pattern categories."""
        return self.patterns
    
    def get_architecture_recommendations(self, context: str, repo_filter: Optional[str] = None) -> str:
        """Generate architecture recommendations based on context + repo."""
        recommendations = []
        context_lower = context.lower()
        
        # Include repo-specific structure if available
        if repo_filter:
            rag = self._get_rag_service()
            if rag:
                try:
                    repo_results = rag.query("import class function module", top_k=3, repo_filter=repo_filter)
                    if repo_results:
                        recommendations.append("## 프로젝트 기존 아키텍처")
                        for r in repo_results:
                            file_path = r.get("metadata", {}).get("file", "")
                            recommendations.append(f"- `{file_path}`")
                        recommendations.append("")
                except Exception as e:
                    logger.warning(f"Repo context failed: {e}")
        
        # Microservices context
        if any(word in context_lower for word in ["microservice", "distributed", "scale"]):
            recommendations.append("## Microservices Recommendations")
            recommendations.append("- Use database per service pattern")
            recommendations.append("- Implement circuit breakers for resilience")
            recommendations.append("- Consider event-driven communication")
            recommendations.append("- Set up distributed tracing")
        
        # DDD context
        if any(word in context_lower for word in ["domain", "entity", "aggregate"]):
            recommendations.append("\n## DDD Recommendations")
            recommendations.append("- Define bounded contexts clearly")
            recommendations.append("- Use aggregates for consistency boundaries")
            recommendations.append("- Implement repository pattern")
            recommendations.append("- Apply ubiquitous language")
        
        # Event-driven context
        if any(word in context_lower for word in ["event", "async", "queue", "message"]):
            recommendations.append("\n## Event-Driven Recommendations")
            recommendations.append("- Consider event sourcing for audit trail")
            recommendations.append("- Use outbox pattern for reliability")
            recommendations.append("- Implement idempotent event handlers")
            recommendations.append("- Plan for eventual consistency")
        
        # General recommendations
        recommendations.append("\n## General Recommendations")
        recommendations.append("- Follow Clean Architecture dependency rule")
        recommendations.append("- Apply AWS Well-Architected principles")
        recommendations.append("- Implement proper observability")
        
        return "\n".join(recommendations)


# MCP Server entry point
def create_server():
    """Create and return the MCP server instance."""
    return ArchRagServer()


if __name__ == "__main__":
    # Simple test
    server = create_server()
    results = server.query("saga distributed transaction", repo_filter="RemoteDeveloper")
    for r in results:
        print(f"{r['category']}: score={r['score']}")
