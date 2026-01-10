import redis
import json
import uuid
import datetime
import argparse
import sys
import random

# Redis Config
REDIS_HOST = 'localhost'
REDIS_PORT = 6379
REDIS_DB = 0

# All 10 agents in order
AGENT_STAGES = [
    "REQUIREMENT",
    "PLAN",
    "UXUI",
    "ARCHITECT",
    "CODE",
    "REFACTORING",
    "TESTQA",
    "DOC",
    "RELEASE",
    "MONITORING"
]

def get_redis_connection():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        return r
    except redis.ConnectionError:
        print("Error: Could not connect to Redis. Is it running?")
        sys.exit(1)

def generate_event(stage="REQUIREMENT", prompt="Create a snake game in Python"):
    event_id = f"evt_{str(uuid.uuid4())}"
    timestamp = datetime.datetime.now().isoformat()
    
    user_id = random.randint(100000, 999999)
    chat_id = random.randint(100000000, 999999999)

    event = {
        "meta": {
            "event_id": event_id,
            "trace_id": f"trc_{str(uuid.uuid4())}",
            "timestamp": timestamp,
            "source": "dummy_generator",
            "version": "1.0"
        },
        "context": {
            "user_id": user_id,
            "chat_id": chat_id,
            "platform": "test_script"
        },
        "task": {
            "title": f"Task-{event_id[-8:]}",
            "type": "CODE_ORCHESTRATION",
            "status": "PENDING",
            "current_stage": stage,
            "needs_clarification": False,
            "clarification_question": None,
            "original_prompt": prompt,
            "git_context": {
                "repo_url": "https://github.com/example/repo.git",
                "branch_name": "main"
            }
        },
        "data": {
            "requirement": None,
            "plan": None,
            "ux_ui": None,
            "architecture": None,
            "code": None,
            "refactoring": None,
            "test_results": None,
            "documentation": None,
            "release": None,
            "monitoring": None,
            "artifacts": []
        },
        "history": [
            {
                "stage": "GENERATED",
                "timestamp": timestamp,
                "message": f"Dummy event generated for stage {stage}"
            }
        ]
    }
    return event

def main():
    parser = argparse.ArgumentParser(description="Generate dummy events for Redis queues (10-agent system)")
    parser.add_argument(
        "stage", 
        nargs="?", 
        default="REQUIREMENT", 
        choices=AGENT_STAGES,
        help="Target stage (queue). Default: REQUIREMENT"
    )
    parser.add_argument("--prompt", default="파이썬으로 TODO 앱 만들어줘", help="Task prompt")
    parser.add_argument("--count", type=int, default=1, help="Number of events to generate")
    parser.add_argument("--list", action="store_true", help="List all available stages")
    
    args = parser.parse_args()
    
    if args.list:
        print("Available agent stages:")
        for i, stage in enumerate(AGENT_STAGES, 1):
            print(f"  {i}. {stage}")
        return
    
    r = get_redis_connection()
    queue_name = f"queue:{args.stage}"
    
    print(f"Generating {args.count} event(s) for {queue_name}...")
    print(f"Prompt: {args.prompt}")
    print()
    
    for i in range(args.count):
        prompt = f"{args.prompt}" if args.count == 1 else f"{args.prompt} ({i+1})"
        event = generate_event(stage=args.stage, prompt=prompt)
        r.rpush(queue_name, json.dumps(event))
        print(f"  [{i+1}] Pushed event {event['meta']['event_id']} to {queue_name}")
    
    print()
    print("Done. Use the following to process:")
    print(f"  curl -X POST http://localhost:8001/agent/{args.stage.lower()}/process")

if __name__ == "__main__":
    main()
