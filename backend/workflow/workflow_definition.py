"""
Workflow Definition Module - Data-driven state machine definitions.

This module defines the structure for workflows and provides the 
product_dev_v1 workflow configuration with all 10 agents.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Action:
    """
    Action to execute on state enter or transition.
    
    Attributes:
        enqueue_agent: Agent name to enqueue (e.g., "REQUIREMENT", "PLAN")
        params: Additional parameters for the agent job
    """
    enqueue_agent: str
    params: Dict[str, str] = field(default_factory=dict)


@dataclass
class Transition:
    """
    Defines a state transition triggered by an event.
    
    Attributes:
        to_state: Target state after transition
        actions: Additional actions to execute on transition
    """
    to_state: str
    actions: List[Action] = field(default_factory=list)


@dataclass
class StateDefinition:
    """
    Defines a state in the workflow.
    
    Attributes:
        on_enter: Actions to execute when entering this state
        transitions: Map of event_name -> Transition
        requires_approvals: List of approval flags needed (for multi-approval states)
    """
    on_enter: List[Action] = field(default_factory=list)
    transitions: Dict[str, Transition] = field(default_factory=dict)
    requires_approvals: List[str] = field(default_factory=list)


@dataclass
class WorkflowDefinition:
    """
    Complete workflow definition.
    
    Attributes:
        name: Unique workflow identifier
        initial_state: Starting state for new WorkItems
        states: Map of state_name -> StateDefinition
    """
    name: str
    initial_state: str
    states: Dict[str, StateDefinition]


# =============================================================================
# PRODUCT DEVELOPMENT WORKFLOW (v1)
# =============================================================================
# 10 Agents: REQUIREMENT -> PLAN -> UXUI/ARCHITECT -> CODE -> REFACTORING 
#            -> TESTQA -> DOC -> RELEASE -> MONITORING
#
# Special features:
# - DESIGN state requires both UX_APPROVED and ARCH_APPROVED
# - Multiple backward transitions for agile iteration
# =============================================================================

PRODUCT_DEV_V1 = WorkflowDefinition(
    name="product_dev_v1",
    initial_state="REQUIREMENTS",
    states={
        # State 1: Requirements Refinement
        "REQUIREMENTS": StateDefinition(
            on_enter=[Action(enqueue_agent="REQUIREMENT")],
            transitions={
                "REQUIREMENTS_COMPLETED": Transition(to_state="PLANNING"),
                "REQUIREMENTS_NEEDS_MORE_INFO": Transition(to_state="REQUIREMENTS"),
            }
        ),
        
        # State 2: Planning (Roadmap/Task Decomposition)
        "PLANNING": StateDefinition(
            on_enter=[Action(enqueue_agent="PLAN")],
            transitions={
                "PLAN_COMPLETED": Transition(to_state="DESIGN"),
                "PLAN_SCOPE_CHANGED": Transition(to_state="REQUIREMENTS"),
            }
        ),
        
        # State 3: Design (UX + Architecture) - Parallel agents, requires both approvals
        "DESIGN": StateDefinition(
            on_enter=[
                Action(enqueue_agent="UXUI"),
                Action(enqueue_agent="ARCHITECT"),
            ],
            transitions={
                # Individual approval events (tracked via approval_flags)
                "UX_APPROVED": Transition(to_state="DESIGN"),  # Stay in DESIGN, check flags
                "ARCH_APPROVED": Transition(to_state="DESIGN"),  # Stay in DESIGN, check flags
                # Combined approval - auto-generated when both flags are set
                "UX_ARCH_DONE": Transition(to_state="CODING"),
                # Rejection goes back to requirements
                "DESIGN_REJECTED": Transition(to_state="REQUIREMENTS"),
            },
            requires_approvals=["UX_APPROVED", "ARCH_APPROVED"]
        ),
        
        # State 4: Coding (Implementation)
        "CODING": StateDefinition(
            on_enter=[Action(enqueue_agent="CODE")],
            transitions={
                "CODE_READY_FOR_QA": Transition(to_state="QA"),
                "CODE_NEEDS_REFACTOR": Transition(to_state="REFACTOR"),
            }
        ),
        
        # State 5: Refactoring
        "REFACTOR": StateDefinition(
            on_enter=[Action(enqueue_agent="REFACTORING")],
            transitions={
                "REFACTOR_DONE": Transition(to_state="CODING"),
            }
        ),
        
        # State 6: QA (Testing/Verification)
        "QA": StateDefinition(
            on_enter=[Action(enqueue_agent="TESTQA")],
            transitions={
                "QA_PASSED": Transition(to_state="DOC"),
                "QA_FAILED": Transition(to_state="CODING"),
                "QA_SCOPE_CHANGE": Transition(to_state="REQUIREMENTS"),
            }
        ),
        
        # State 7: Documentation
        "DOC": StateDefinition(
            on_enter=[Action(enqueue_agent="DOC")],
            transitions={
                "DOC_DONE": Transition(to_state="RELEASE"),
            }
        ),
        
        # State 8: Release (Deployment)
        "RELEASE": StateDefinition(
            on_enter=[Action(enqueue_agent="RELEASE")],
            transitions={
                "RELEASED": Transition(to_state="MONITORING"),
                "RELEASE_REJECTED": Transition(to_state="QA"),
            }
        ),
        
        # State 9: Monitoring (VOC Collection)
        "MONITORING": StateDefinition(
            on_enter=[Action(enqueue_agent="MONITORING")],
            transitions={
                "INCIDENT_HOTFIX": Transition(to_state="CODING"),
                "NEW_FEATURE_IDEA": Transition(to_state="REQUIREMENTS"),
                "MONITORING_COMPLETE": Transition(to_state="DONE"),
            }
        ),
        
        # Terminal State
        "DONE": StateDefinition(
            on_enter=[],
            transitions={}
        ),
    }
)


# =============================================================================
# WORKFLOW REGISTRY
# =============================================================================

WORKFLOW_REGISTRY: Dict[str, WorkflowDefinition] = {
    "product_dev_v1": PRODUCT_DEV_V1,
}


def get_workflow(name: str) -> Optional[WorkflowDefinition]:
    """Get workflow definition by name."""
    return WORKFLOW_REGISTRY.get(name)


def list_workflows() -> List[str]:
    """List all available workflow names."""
    return list(WORKFLOW_REGISTRY.keys())
