"""
Agents Module - Agent registry and exports.
"""
from typing import Dict, List

from .base import AgentStrategy
from .implementations import (
    RequirementAgent,
    PlanAgent,
    UxUiAgent,
    ArchitectAgent,
    CodeAgent,
    RefactoringAgent,
    TestQaAgent,
    DocAgent,
    ReleaseAgent,
    MonitoringAgent,
)

# =============================================================================
# AGENT REGISTRY
# =============================================================================

AGENT_REGISTRY: Dict[str, AgentStrategy] = {
    "REQUIREMENT": RequirementAgent(),
    "PLAN": PlanAgent(),
    "UXUI": UxUiAgent(),
    "ARCHITECT": ArchitectAgent(),
    "CODE": CodeAgent(),
    "REFACTORING": RefactoringAgent(),
    "TESTQA": TestQaAgent(),
    "DOC": DocAgent(),
    "RELEASE": ReleaseAgent(),
    "MONITORING": MonitoringAgent(),
}

AGENT_ORDER: List[str] = [
    "REQUIREMENT", "PLAN", "UXUI", "ARCHITECT", "CODE",
    "REFACTORING", "TESTQA", "DOC", "RELEASE", "MONITORING"
]

__all__ = [
    "AgentStrategy",
    "AGENT_REGISTRY",
    "AGENT_ORDER",
    "RequirementAgent",
    "PlanAgent",
    "UxUiAgent",
    "ArchitectAgent",
    "CodeAgent",
    "RefactoringAgent",
    "TestQaAgent",
    "DocAgent",
    "ReleaseAgent",
    "MonitoringAgent",
]
