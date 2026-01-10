#!/usr/bin/env python3
"""
Test script for Workflow Engine.

Usage:
    cd /Users/yprite/IdeaProjects/Cursor_pro/RemoteDevelop
    source venv/bin/activate
    python test/test_workflow.py
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

import redis
from datetime import datetime

from workflow import Orchestrator, WORKFLOW_REGISTRY, PRODUCT_DEV_V1
from models import WorkItem, WorkflowEvent, EventNames


def test_workflow_definition():
    """Test workflow definition structure."""
    print("\n=== Test: Workflow Definition ===")
    
    wf = PRODUCT_DEV_V1
    print(f"Workflow name: {wf.name}")
    print(f"Initial state: {wf.initial_state}")
    print(f"States: {list(wf.states.keys())}")
    
    # Check state count
    assert len(wf.states) == 10, f"Expected 10 states, got {len(wf.states)}"
    
    # Check initial state
    assert wf.initial_state == "REQUIREMENTS"
    
    # Check DESIGN state requires approvals
    design_state = wf.states["DESIGN"]
    assert "UX_APPROVED" in design_state.requires_approvals
    assert "ARCH_APPROVED" in design_state.requires_approvals
    
    print("✓ Workflow definition is correct")


def test_workitem_creation():
    """Test WorkItem creation."""
    print("\n=== Test: WorkItem Creation ===")
    
    wi = WorkItem.create("Test Feature", {"priority": "high"})
    
    print(f"ID: {wi.id}")
    print(f"Title: {wi.title}")
    print(f"State: {wi.current_state}")
    print(f"Meta: {wi.meta}")
    
    assert wi.id.startswith("wi_")
    assert wi.title == "Test Feature"
    assert wi.current_state == "REQUIREMENTS"
    assert wi.meta.get("priority") == "high"
    
    print("✓ WorkItem creation works")


def test_workflow_event():
    """Test WorkflowEvent creation."""
    print("\n=== Test: WorkflowEvent ===")
    
    event = WorkflowEvent(
        name=EventNames.REQUIREMENTS_COMPLETED,
        work_item_id="wi_test123",
        payload={"details": "test"}
    )
    
    print(f"Event: {event.name}")
    print(f"WorkItem ID: {event.work_item_id}")
    
    # Test serialization
    json_str = event.to_json()
    restored = WorkflowEvent.from_json(json_str)
    
    assert restored.name == event.name
    assert restored.work_item_id == event.work_item_id
    
    print("✓ WorkflowEvent works")


def test_orchestrator_with_redis():
    """Test Orchestrator with Redis (if available)."""
    print("\n=== Test: Orchestrator ===")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        print("Redis connected")
    except redis.ConnectionError:
        print("⚠ Redis not available, skipping orchestrator test")
        return
    
    orch = Orchestrator(r)
    
    # Create WorkItem
    wi = orch.create_work_item("Orchestrator Test", {"test": True})
    print(f"Created WorkItem: {wi.id}")
    
    # Verify it's saved
    loaded = orch.load_work_item(wi.id)
    assert loaded is not None
    assert loaded.current_state == "REQUIREMENTS"
    print(f"Initial state: {loaded.current_state}")
    
    # Trigger transition: REQUIREMENTS_COMPLETED
    event = WorkflowEvent(
        name="REQUIREMENTS_COMPLETED",
        work_item_id=wi.id
    )
    success, msg = orch.handle_event(event)
    assert success, f"Transition failed: {msg}"
    print(f"Transition result: {msg}")
    
    # Verify new state
    loaded = orch.load_work_item(wi.id)
    assert loaded.current_state == "PLANNING"
    print(f"After REQUIREMENTS_COMPLETED: {loaded.current_state}")
    
    # Trigger next transition: PLAN_COMPLETED
    event = WorkflowEvent(name="PLAN_COMPLETED", work_item_id=wi.id)
    success, msg = orch.handle_event(event)
    assert success
    
    loaded = orch.load_work_item(wi.id)
    assert loaded.current_state == "DESIGN"
    print(f"After PLAN_COMPLETED: {loaded.current_state}")
    
    # Test multi-approval in DESIGN state
    print("\nTesting multi-approval in DESIGN state:")
    
    # First approval: UX
    success, msg = orch.submit_approval(wi.id, "UX", approved=True)
    assert success
    print(f"  UX approval: {msg}")
    
    loaded = orch.load_work_item(wi.id)
    print(f"  State after UX: {loaded.current_state}, flags: {loaded.approval_flags}")
    assert loaded.current_state == "DESIGN"  # Still in DESIGN
    
    # Second approval: ARCH
    success, msg = orch.submit_approval(wi.id, "ARCH", approved=True)
    assert success
    print(f"  ARCH approval: {msg}")
    
    loaded = orch.load_work_item(wi.id)
    print(f"  State after ARCH: {loaded.current_state}")
    assert loaded.current_state == "CODING"  # Now moved to CODING
    
    # Test backward transition: CODE_NEEDS_REFACTOR
    event = WorkflowEvent(name="CODE_NEEDS_REFACTOR", work_item_id=wi.id)
    success, msg = orch.handle_event(event)
    assert success
    
    loaded = orch.load_work_item(wi.id)
    print(f"\nAfter CODE_NEEDS_REFACTOR: {loaded.current_state}")
    assert loaded.current_state == "REFACTOR"
    
    # Cleanup
    orch.delete_work_item(wi.id)
    print("\n✓ Orchestrator tests passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("Workflow Engine Test Suite")
    print("=" * 60)
    
    test_workflow_definition()
    test_workitem_creation()
    test_workflow_event()
    test_orchestrator_with_redis()
    
    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
