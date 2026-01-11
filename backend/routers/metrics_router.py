from fastapi import APIRouter
from core.metrics_service import MetricsService

router = APIRouter(tags=["Metrics"])
metrics_service = MetricsService()

@router.get("/metrics/agents")
def get_all_agent_metrics():
    """Get performance metrics for all agents."""
    stats = metrics_service.get_all_stats()
    
    # Calculate success rates
    for agent_name, data in stats.items():
        total = data.get("total", 0)
        if total > 0:
            data["success_rate"] = round(data.get("success", 0) / total * 100, 1)
        else:
            data["success_rate"] = 0
    
    return {"agents": stats}

@router.get("/metrics/agent/{agent_name}")
def get_agent_metrics(agent_name: str):
    """Get performance metrics for a specific agent."""
    stats = metrics_service.get_agent_stats(agent_name)
    total = stats.get("total", 0)
    if total > 0:
        stats["success_rate"] = round(stats.get("success", 0) / total * 100, 1)
    else:
        stats["success_rate"] = 0
    return {"agent": agent_name, "stats": stats}

@router.get("/metrics/improvements")
def get_improvements():
    """Get recent improvement suggestions."""
    improvements = metrics_service.get_improvements(limit=20)
    return {"improvements": improvements}

@router.delete("/metrics/clear")
def clear_metrics():
    """Clear all metrics (admin only)."""
    metrics_service.clear_stats()
    return {"status": "cleared"}
