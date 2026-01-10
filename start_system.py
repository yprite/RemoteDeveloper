import subprocess
import time
import os
import signal
import sys
import re
import threading
import argparse

# Configuration
N8N_PORT = 5678
AGENT_PORT = 8001
REDIS_PORT = 6379
DASHBOARD_PORT = 5173

VENV_PYTHON = "./venv/bin/python"  # Path to venv python
CLOUDFLARED_PATH = "./cloudflare/cloudflared" # Path to cloudflared binary
REDIS_SERVER_PATH = "/opt/homebrew/opt/redis/bin/redis-server"
REDIS_CONF_PATH = "/opt/homebrew/etc/redis.conf"
BACKEND_PATH = "./backend"

processes = []

def log(msg):
    print(f"[System Launcher] {msg}")

def kill_process_on_port(port):
    """Kills any process listening on the specified port."""
    try:
        # Find PID using lsof
        result = subprocess.run(f"lsof -t -i:{port}", shell=True, capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        for pid in pids:
            if pid:
                log(f"Killing process {pid} on port {port}...")
                subprocess.run(f"kill -9 {pid}", shell=True)
    except Exception as e:
        log(f"Error killing process on port {port}: {e}")

def cleanup():
    """Terminates all started processes."""
    log("Shutting down services...")
    for p in processes:
        if p.poll() is None: # If process is still running
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
    log("All services stopped.")
    sys.exit(0)

def signal_handler(sig, frame):
    cleanup()

def stream_reader(pipe, prefix):
    """Reads output from a subprocess pipe and prints it."""
    try:
        if pipe:
            for line in iter(pipe.readline, ''):
                print(f"[{prefix}] {line.strip()}")
            pipe.close()
    except ValueError:
        pass

def find_tunnel_url(pipe):
    """Reads cloudflared output to find the tunnel URL."""
    url = None
    # Regex to capture https://<random>.trycloudflare.com
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    
    for line in iter(pipe.readline, ''):
        print(f"[Cloudflared] {line.strip()}")
        if not url:
            match = url_pattern.search(line)
            if match:
                url = match.group(0)
                return url
    return None

def main():
    parser = argparse.ArgumentParser(description="Start the AI System Services")
    parser.add_argument("--all", action="store_true", help="Start all services (Default)")
    parser.add_argument("--redis", action="store_true", help="Start Redis")
    parser.add_argument("--agent", action="store_true", help="Start Code Agent API")
    parser.add_argument("--n8n", action="store_true", help="Start n8n & Tunnel")
    parser.add_argument("--dashboard", action="store_true", help="Start Frontend Dashboard")
    
    args = parser.parse_args()
    
    # Default to all if no specific service requested
    if not any([args.redis, args.agent, args.n8n, args.dashboard]):
        args.all = True

    run_redis = args.all or args.redis
    run_agent = args.all or args.agent
    run_n8n = args.all or args.n8n
    run_dashboard = args.all or args.dashboard

    # Register signal handlers for graceful shutdown (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 1. Clean up ports
    log("Cleaning up ports...")
    if run_n8n: kill_process_on_port(N8N_PORT)
    if run_agent: kill_process_on_port(AGENT_PORT)
    if run_redis: kill_process_on_port(REDIS_PORT)
    if run_dashboard: kill_process_on_port(DASHBOARD_PORT)

    # 2. Start Redis
    if run_redis:
        log("Starting Redis...")
        redis_cmd = [REDIS_SERVER_PATH, REDIS_CONF_PATH]
        redis_proc = subprocess.Popen(
            redis_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        processes.append(redis_proc)
        threading.Thread(target=stream_reader, args=(redis_proc.stdout, "Redis"), daemon=True).start()
        time.sleep(1) # Wait for Redis to warm up

    # 3. Start Code Agent (FastAPI)
    if run_agent:
        log("Starting Code Agent (FastAPI)...")
        agent_cmd = [VENV_PYTHON, f"{BACKEND_PATH}/main.py"]
        agent_proc = subprocess.Popen(
            agent_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.getcwd()
        )
        processes.append(agent_proc)
        threading.Thread(target=stream_reader, args=(agent_proc.stdout, "Agent-Out"), daemon=True).start()
        threading.Thread(target=stream_reader, args=(agent_proc.stderr, "Agent-Err"), daemon=True).start()
        time.sleep(1)

    # 4. Start Cloudflare Tunnel & n8n
    if run_n8n:
        log("Starting Cloudflare Tunnel...")
        tunnel_cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{N8N_PORT}"]
        tunnel_proc = subprocess.Popen(
            tunnel_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, # Cloudflared logs to stderr usually
            text=True,
            cwd=os.getcwd()
        )
        processes.append(tunnel_proc)

        # We need to capture the URL from stderr/stdout
        tunnel_url = find_tunnel_url(tunnel_proc.stderr)
        
        if tunnel_url:
            log(f"Tunnel established at: {tunnel_url}")
            # Keep reading the rest of the logs in background
            threading.Thread(target=stream_reader, args=(tunnel_proc.stderr, "Cloudflared"), daemon=True).start()
            
            # 5. Start n8n
            log(f"Starting n8n with WEBHOOK_URL={tunnel_url}...")
            env = os.environ.copy()
            env["WEBHOOK_URL"] = tunnel_url
            env["N8N_BLOCK_PRIVATE_IPS"] = "false"
            
            n8n_cmd = ["n8n", "start"]
            n8n_proc = subprocess.Popen(
                n8n_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=os.getcwd()
            )
            processes.append(n8n_proc)
            threading.Thread(target=stream_reader, args=(n8n_proc.stdout, "n8n-Out"), daemon=True).start()
            threading.Thread(target=stream_reader, args=(n8n_proc.stderr, "n8n-Err"), daemon=True).start()
        else:
            log("Failed to find tunnel URL. Skipping n8n start.")
            # Don't exit, other services might be running

    # 6. Start Frontend Dashboard
    if run_dashboard:
        log("Starting Frontend Dashboard...")
        dashboard_cmd = ["npm", "run", "dev", "--", "--port", str(DASHBOARD_PORT)]
        dashboard_proc = subprocess.Popen(
            dashboard_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=os.path.join(os.getcwd(), "dashboard")
        )
        processes.append(dashboard_proc)
        threading.Thread(target=stream_reader, args=(dashboard_proc.stdout, "Dash-Out"), daemon=True).start()
        threading.Thread(target=stream_reader, args=(dashboard_proc.stderr, "Dash-Err"), daemon=True).start()
        log(f"Dashboard accessible at http://localhost:{DASHBOARD_PORT}")

    log("Selected services are running! Press Ctrl+C to stop.")
    
    # Keep the main thread alive watching processes
    while True:
        if not processes:
            log("No processes running. Exiting.")
            sys.exit(0)
            
        for p in processes:
            if p.poll() is not None:
                log(f"A process has died! (Return Code: {p.returncode})")
                # Remove dead process? Or shutdown all?
                # For now let's cleanup all if one important one dies
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
