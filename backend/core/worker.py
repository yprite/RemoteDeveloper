"""
Background Worker - Automatically processes agent queues.
"""
import asyncio
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger("worker")

# Worker state
_worker_thread: Optional[threading.Thread] = None
_worker_running = False


def process_queues_once():
    """Process one item from each queue that has items."""
    from agents import AGENT_REGISTRY, AGENT_ORDER
    from core.redis_client import pop_event, push_event, get_redis
    from core.logging_config import add_log
    import json
    from datetime import datetime
    
    r = get_redis()
    if not r:
        return
    
    for agent_name in AGENT_ORDER:
        queue_name = f"queue:{agent_name}"
        
        # Check if queue has items
        queue_len = r.llen(queue_name)
        if queue_len == 0:
            continue
        
        # Pop and process
        event = pop_event(queue_name)
        if not event:
            continue
        
        agent = AGENT_REGISTRY.get(agent_name)
        if not agent:
            continue
        
        event_id = event.get('meta', {}).get('event_id', 'unknown')
        add_log(agent_name, f"Processing {event_id}", "running")
        
        try:
            # Process event
            event = agent.process(event)
            
            # Check for clarification (REQUIREMENT agent)
            if agent_name == "REQUIREMENT" and event.get("task", {}).get("needs_clarification"):
                waiting_key = f"waiting:clarification:{event_id}"
                r.set(waiting_key, json.dumps(event))
                add_log(agent_name, f"Waiting for clarification: {event_id}", "pending")
                
                # Telegram notification
                from core.telegram_bot import send_telegram_notification
                chat_id = event.get("context", {}).get("chat_id")
                if chat_id:
                    send_telegram_notification(
                        str(chat_id),
                        f"❓ <b>추가 정보가 필요합니다</b>\n\n{event['task'].get('clarification_question')}"
                    )
                continue
            
            # Update task status
            next_agent = agent.next_agent
            event["task"]["current_stage"] = next_agent if next_agent else "DONE"
            if not next_agent:
                event["task"]["status"] = "COMPLETED"
            
            # Update history
            event["history"].append({
                "stage": agent_name,
                "timestamp": datetime.now().isoformat(),
                "message": f"Processed by {agent.display_name}"
            })
            
            # Push to next queue or finish
            if next_agent:
                push_event(f"queue:{next_agent}", event)
                add_log(agent_name, f"Completed {event_id} → {next_agent}", "success")
            else:
                add_log("SYSTEM", f"Pipeline completed for {event_id}", "success")
                
        except Exception as e:
            logger.error(f"Worker error processing {event_id}: {e}")
            add_log(agent_name, f"Error: {str(e)[:100]}", "failed")
            # Re-queue on error? For now, just log and continue


def worker_loop():
    """Background worker loop."""
    global _worker_running
    
    logger.info("Background worker started")
    
    while _worker_running:
        try:
            process_queues_once()
        except Exception as e:
            logger.error(f"Worker loop error: {e}")
        
        # Sleep between iterations (adjust as needed)
        time.sleep(2)
    
    logger.info("Background worker stopped")


def start_worker():
    """Start the background worker thread."""
    global _worker_thread, _worker_running
    
    if _worker_running:
        logger.info("Worker already running")
        return
    
    _worker_running = True
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()
    logger.info("Background worker thread started")


def stop_worker():
    """Stop the background worker thread."""
    global _worker_running
    _worker_running = False
    logger.info("Background worker stopping...")
