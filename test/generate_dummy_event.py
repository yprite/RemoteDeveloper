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

def get_redis_connection():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
        r.ping()
        return r
    except redis.ConnectionError:
        print("Error: Could not connect to Redis. Is it running?")
        sys.exit(1)

def generate_event(stage="PLAN", prompt="Create a snake game in Python"):
    event_id = f"evt_{str(uuid.uuid4())}"
    timestamp = datetime.datetime.now().isoformat()
    
    # Random IDs
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
            "original_prompt": prompt,
            "git_context": {
                "repo_url": "https://github.com/example/repo.git",
                "branch_name": "main"
            }
        },
        "data": {
            "plan": None,
            "code": None,
            "test_results": None,
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
    parser = argparse.ArgumentParser(description="Generate dummy events for Redis queues")
    parser.add_argument("stage", nargs="?", default="PLAN", choices=["PLAN", "IMPLEMENTATION", "TEST"], help="Target stage (queue)")
    parser.add_argument("--prompt", default="Create a Calculator App", help="Task prompt")
    parser.add_argument("--count", type=int, default=1, help="Number of events to generate")
    
    args = parser.parse_args()
    
    r = get_redis_connection()
    queue_name = f"queue:{args.stage}"
    
    print(f"Generating {args.count} event(s) for {queue_name}...")
    
    for i in range(args.count):
        event = generate_event(stage=args.stage, prompt=f"{args.prompt} ({i+1})")
        r.rpush(queue_name, json.dumps(event))
        print(f"  [{i+1}] Pushed event {event['meta']['event_id']} to {queue_name}")
        
    print("Done.")

if __name__ == "__main__":
    main()
