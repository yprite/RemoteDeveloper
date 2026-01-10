"""
Orchestrator Module - State machine engine that handles events and transitions.

The Orchestrator is responsible for:
1. Loading WorkItems from Redis storage
2. Processing incoming events
3. Executing state transitions
4. Triggering on_enter actions (enqueue agent jobs)
5. Handling multi-approval logic (e.g., DESIGN state)
"""
import json
import logging
from datetime import datetime
from typing import Optional, List, Tuple

import redis

from models import WorkItem, WorkflowEvent
from workflow.workflow_definition import (
    WorkflowDefinition,
    StateDefinition,
    Action,
    WORKFLOW_REGISTRY,
)


logger = logging.getLogger(__name__)


class Orchestrator:
    """
    State machine orchestrator for workflow management.
    
    This class handles:
    - WorkItem persistence (Redis-based)
    - Event processing and state transitions
    - Agent job enqueuing
    - Multi-approval state handling
    """
    
    # Redis key prefixes
    WORKITEM_PREFIX = "workitem:"
    WORKITEM_INDEX = "workitem:index"
    
    def __init__(self, redis_client: redis.Redis):
        """
        Initialize orchestrator with Redis connection.
        
        Args:
            redis_client: Connected Redis client
        """
        self.redis = redis_client
    
    # =========================================================================
    # WORKITEM PERSISTENCE
    # =========================================================================
    
    def save_work_item(self, work_item: WorkItem) -> None:
        """Save WorkItem to Redis."""
        key = f"{self.WORKITEM_PREFIX}{work_item.id}"
        self.redis.set(key, work_item.to_json())
        # Add to index for listing
        self.redis.sadd(self.WORKITEM_INDEX, work_item.id)
        logger.info(f"Saved WorkItem {work_item.id} to Redis")
    
    def load_work_item(self, work_item_id: str) -> Optional[WorkItem]:
        """Load WorkItem from Redis."""
        key = f"{self.WORKITEM_PREFIX}{work_item_id}"
        data = self.redis.get(key)
        if data:
            return WorkItem.from_json(data)
        return None
    
    def delete_work_item(self, work_item_id: str) -> bool:
        """Delete WorkItem from Redis."""
        key = f"{self.WORKITEM_PREFIX}{work_item_id}"
        result = self.redis.delete(key)
        self.redis.srem(self.WORKITEM_INDEX, work_item_id)
        return result > 0
    
    def list_work_items(self) -> List[WorkItem]:
        """List all WorkItems."""
        work_items = []
        ids = self.redis.smembers(self.WORKITEM_INDEX)
        for work_item_id in ids:
            wi = self.load_work_item(work_item_id)
            if wi:
                work_items.append(wi)
        return work_items
    
    # =========================================================================
    # WORKFLOW OPERATIONS
    # =========================================================================
    
    def get_workflow(self, workflow_name: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition by name."""
        return WORKFLOW_REGISTRY.get(workflow_name)
    
    def create_work_item(
        self, 
        title: str, 
        meta: Optional[dict] = None,
        workflow_name: str = "product_dev_v1"
    ) -> WorkItem:
        """
        Create a new WorkItem and trigger initial state entry.
        
        Args:
            title: Human-readable title
            meta: Optional metadata (priority, tags, etc.)
            workflow_name: Workflow to use (default: product_dev_v1)
            
        Returns:
            Created WorkItem with initial state actions triggered
        """
        # Create WorkItem
        work_item = WorkItem.create(title, meta, workflow_name)
        
        # Get workflow and initial state
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        # Save WorkItem
        self.save_work_item(work_item)
        
        # Execute on_enter actions for initial state
        initial_state = workflow.states.get(work_item.current_state)
        if initial_state:
            self._execute_actions(work_item, initial_state.on_enter)
        
        logger.info(f"Created WorkItem {work_item.id} with initial state {work_item.current_state}")
        return work_item
    
    def handle_event(self, event: WorkflowEvent) -> Tuple[bool, str]:
        """
        Process a workflow event and perform state transition.
        
        Args:
            event: WorkflowEvent to process
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Load WorkItem
        work_item = self.load_work_item(event.work_item_id)
        if not work_item:
            return False, f"WorkItem not found: {event.work_item_id}"
        
        # Load Workflow
        workflow = self.get_workflow(work_item.workflow_name)
        if not workflow:
            return False, f"Workflow not found: {work_item.workflow_name}"
        
        # Get current state definition
        current_state_def = workflow.states.get(work_item.current_state)
        if not current_state_def:
            return False, f"Invalid state: {work_item.current_state}"
        
        # Check for multi-approval states (e.g., DESIGN)
        if current_state_def.requires_approvals:
            result = self._handle_approval_event(
                work_item, workflow, current_state_def, event
            )
            if result:
                return result
        
        # Find transition for this event
        transition = current_state_def.transitions.get(event.name)
        if not transition:
            return False, f"Invalid transition: state={work_item.current_state}, event={event.name}"
        
        # Execute state transition
        previous_state = work_item.current_state
        work_item.current_state = transition.to_state
        work_item.add_history(
            transition.to_state,
            f"Transitioned from {previous_state} via {event.name}"
        )
        
        # Clear approval flags when leaving approval-required states
        if current_state_def.requires_approvals:
            work_item.approval_flags = {}
        
        # Save updated WorkItem
        self.save_work_item(work_item)
        
        # Execute transition actions
        self._execute_actions(work_item, transition.actions)
        
        # Execute on_enter actions for new state
        new_state_def = workflow.states.get(work_item.current_state)
        if new_state_def:
            self._execute_actions(work_item, new_state_def.on_enter)
        
        logger.info(
            f"WorkItem {work_item.id}: {previous_state} -> {work_item.current_state} "
            f"(event: {event.name})"
        )
        
        return True, f"Transitioned to {work_item.current_state}"
    
    def _handle_approval_event(
        self,
        work_item: WorkItem,
        workflow: WorkflowDefinition,
        state_def: StateDefinition,
        event: WorkflowEvent
    ) -> Optional[Tuple[bool, str]]:
        """
        Handle events for states requiring multiple approvals.
        
        Returns None to continue normal processing, or a result tuple to return early.
        """
        # Check if this is an approval event
        if event.name in state_def.requires_approvals:
            # Set approval flag
            work_item.approval_flags[event.name] = True
            work_item.add_history(
                work_item.current_state,
                f"Approval received: {event.name}"
            )
            
            # Check if all approvals received
            all_approved = all(
                work_item.approval_flags.get(approval, False)
                for approval in state_def.requires_approvals
            )
            
            if all_approved:
                # Generate combined approval event
                # For DESIGN state, this generates UX_ARCH_DONE
                combined_event_name = self._get_combined_approval_event(state_def)
                if combined_event_name:
                    # Find transition for combined event
                    transition = state_def.transitions.get(combined_event_name)
                    if transition and transition.to_state != work_item.current_state:
                        # Execute transition to next state
                        previous_state = work_item.current_state
                        work_item.current_state = transition.to_state
                        work_item.approval_flags = {}  # Clear flags
                        work_item.add_history(
                            transition.to_state,
                            f"All approvals received, transitioned from {previous_state}"
                        )
                        self.save_work_item(work_item)
                        
                        # Execute on_enter for new state
                        new_state_def = workflow.states.get(work_item.current_state)
                        if new_state_def:
                            self._execute_actions(work_item, new_state_def.on_enter)
                        
                        logger.info(
                            f"WorkItem {work_item.id}: All approvals received, "
                            f"{previous_state} -> {work_item.current_state}"
                        )
                        return True, f"All approvals received. Transitioned to {work_item.current_state}"
            
            # Save with approval flag, stay in current state
            self.save_work_item(work_item)
            pending = [
                a for a in state_def.requires_approvals 
                if not work_item.approval_flags.get(a, False)
            ]
            return True, f"Approval {event.name} recorded. Waiting for: {pending}"
        
        return None
    
    def _get_combined_approval_event(self, state_def: StateDefinition) -> Optional[str]:
        """Get the combined event name for multi-approval completion."""
        # Map approval combinations to combined events
        approvals = frozenset(state_def.requires_approvals)
        
        APPROVAL_COMBINATIONS = {
            frozenset(["UX_APPROVED", "ARCH_APPROVED"]): "UX_ARCH_DONE",
        }
        
        return APPROVAL_COMBINATIONS.get(approvals)
    
    def _execute_actions(self, work_item: WorkItem, actions: List[Action]) -> None:
        """Execute a list of actions for a WorkItem."""
        for action in actions:
            if action.enqueue_agent:
                self.enqueue_agent_job(
                    action.enqueue_agent,
                    work_item.id,
                    action.params
                )
    
    def enqueue_agent_job(
        self, 
        agent_name: str, 
        work_item_id: str, 
        params: Optional[dict] = None
    ) -> None:
        """
        Enqueue a job for an agent.
        
        Args:
            agent_name: Agent to process the job (e.g., "REQUIREMENT", "PLAN")
            work_item_id: WorkItem ID this job relates to
            params: Additional parameters for the job
        """
        queue_name = f"queue:{agent_name}"
        
        job = {
            "work_item_id": work_item_id,
            "agent": agent_name,
            "payload": params or {},
            "created_at": datetime.now().isoformat()
        }
        
        self.redis.rpush(queue_name, json.dumps(job))
        logger.info(f"Enqueued job for {agent_name}: work_item_id={work_item_id}")
    
    # =========================================================================
    # HUMAN APPROVAL API
    # =========================================================================
    
    def submit_approval(
        self, 
        work_item_id: str, 
        approval_type: str,
        approved: bool = True,
        comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Submit a human approval for a WorkItem.
        
        Args:
            work_item_id: WorkItem to approve
            approval_type: Type of approval ("UX", "ARCH", "RELEASE", etc.)
            approved: Whether approved (True) or rejected (False)
            comment: Optional comment
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Map approval types to event names
        APPROVAL_EVENTS = {
            "UX": ("UX_APPROVED", "DESIGN_REJECTED"),
            "ARCH": ("ARCH_APPROVED", "DESIGN_REJECTED"),
            "RELEASE": ("RELEASED", "RELEASE_REJECTED"),
        }
        
        if approval_type not in APPROVAL_EVENTS:
            return False, f"Unknown approval type: {approval_type}"
        
        approve_event, reject_event = APPROVAL_EVENTS[approval_type]
        event_name = approve_event if approved else reject_event
        
        # Create and handle event
        event = WorkflowEvent(
            name=event_name,
            work_item_id=work_item_id,
            payload={"comment": comment} if comment else {},
            source="human"
        )
        
        return self.handle_event(event)
