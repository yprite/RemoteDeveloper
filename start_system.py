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
CONFIG_FILE_PATH = "./dashboard/src/config.js"

processes = []

def load_env_file():
    """Manually load .env file to avoid dependencies in the launcher script."""
    env_path = ".env"
    if os.path.exists(env_path):
        log(f"Loading environment variables from {env_path}")
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Handle quotes
                    value = value.strip()
                    if (value.startswith('"') and value.endswith('"')) or \
                       (value.startswith("'") and value.endswith("'")):
                        value = value[1:-1]
                    os.environ[key] = value

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
    # Kill any lingering cloudflared
    subprocess.run("pkill -f cloudflared", shell=True)
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

def find_tunnel_url(pipe, prefix="Cloudflared"):
    """Reads cloudflared output to find the tunnel URL."""
    url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
    
    # We must read from the pipe without blocking indefinitely if no URL found
    # But usually cloudflared outputs the URL within first few seconds
    while True:
        line = pipe.readline()
        if not line:
            break
        print(f"[{prefix}] {line.strip()}")
        if not url:
            match = url_pattern.search(line)
            if match:
                url = match.group(0)
                # Don't return yet, we want to start a thread to keep reading
                return url, pipe
    return None, pipe

def update_frontend_config(url):
    """Updates the API_BASE_URL in dashboard/src/config.js with the new tunnel URL."""
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            log(f"Config file not found: {CONFIG_FILE_PATH}")
            return
            
        with open(CONFIG_FILE_PATH, 'r') as f:
            content = f.read()
            
        # Replace API_BASE_URL: '...' or "..." with the new URL
        new_content = re.sub(r"API_BASE_URL:.*", f"API_BASE_URL: '{url}',", content)
        
        with open(CONFIG_FILE_PATH, 'w') as f:
            f.write(new_content)
        log(f"Successfully updated {CONFIG_FILE_PATH} with {url}")
    except Exception as e:
        log(f"Error updating config file: {e}")

def main():
    parser = argparse.ArgumentParser(description="Start the AI System Services")
    parser.add_argument("--all", action="store_true", help="Start all services (Default)")
    parser.add_argument("--redis", action="store_true", help="Start Redis")
    parser.add_argument("--agent", action="store_true", help="Start Code Agent API & Tunnel")
    parser.add_argument("--n8n", action="store_true", help="Start n8n & Tunnel")
    parser.add_argument("--dashboard", action="store_true", help="Start Frontend Dashboard & Tunnel")
    
    args = parser.parse_args()
    
    # Load .env file
    load_env_file()
    
    if not any([args.redis, args.agent, args.n8n, args.dashboard]):
        args.all = True

    run_redis = args.all or args.redis
    run_agent = args.all or args.agent
    run_n8n = args.all or args.n8n
    run_dashboard = args.all or args.dashboard
    
    # Initialize URL variables
    be_url = n8n_url = fe_url = "Not Started"

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    log("Cleaning up ports...")
    if run_n8n: kill_process_on_port(N8N_PORT)
    if run_agent: kill_process_on_port(AGENT_PORT)
    if run_redis: kill_process_on_port(REDIS_PORT)
    if run_dashboard: kill_process_on_port(DASHBOARD_PORT)

    # 1. Start Redis
    if run_redis:
        log("Starting Redis...")
        redis_cmd = [REDIS_SERVER_PATH, REDIS_CONF_PATH]
        redis_proc = subprocess.Popen(redis_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(redis_proc)
        threading.Thread(target=stream_reader, args=(redis_proc.stdout, "Redis"), daemon=True).start()
        time.sleep(1)

    # 2. Start Code Agent (FastAPI) & Tunnel
    if run_agent:
        log("Starting Code Agent (FastAPI)...")
        agent_cmd = [VENV_PYTHON, f"{BACKEND_PATH}/main.py"]
        agent_proc = subprocess.Popen(agent_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(agent_proc)
        threading.Thread(target=stream_reader, args=(agent_proc.stdout, "Agent-Out"), daemon=True).start()
        
        log("Starting Backend Cloudflare Tunnel...")
        be_tunnel_cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{AGENT_PORT}"]
        be_tunnel_proc = subprocess.Popen(be_tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(be_tunnel_proc)
        
        be_url, pipe = find_tunnel_url(be_tunnel_proc.stderr, "BE-Tunnel")
        if be_url:
            log(f"Backend Tunnel URL: {be_url}")
            update_frontend_config(be_url)
            threading.Thread(target=stream_reader, args=(pipe, "BE-Tunnel"), daemon=True).start()
        else:
            log("Failed to start Backend Tunnel.")

    # 3. Start n8n & Tunnel
    if run_n8n:
        log("Starting n8n Cloudflare Tunnel...")
        n8n_tunnel_cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{N8N_PORT}"]
        n8n_tunnel_proc = subprocess.Popen(n8n_tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(n8n_tunnel_proc)

        n8n_url, pipe = find_tunnel_url(n8n_tunnel_proc.stderr, "n8n-Tunnel")
        if n8n_url:
            log(f"n8n Tunnel URL: {n8n_url}")
            threading.Thread(target=stream_reader, args=(pipe, "n8n-Tunnel"), daemon=True).start()
            
            log(f"Starting n8n with WEBHOOK_URL={n8n_url}...")
            env = os.environ.copy()
            env["WEBHOOK_URL"] = n8n_url
            env["N8N_BLOCK_PRIVATE_IPS"] = "false"
            n8n_proc = subprocess.Popen(["n8n", "start"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            processes.append(n8n_proc)
            threading.Thread(target=stream_reader, args=(n8n_proc.stdout, "n8n-Out"), daemon=True).start()
        else:
            log("Failed to start n8n Tunnel.")

    # 4. Start Frontend Dashboard & Tunnel
    if run_dashboard:
        log("Starting Frontend Dashboard (Vite)...")
        dashboard_proc = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(DASHBOARD_PORT), "--host", "0.0.0.0"], 
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, 
                                        cwd="./dashboard")
        processes.append(dashboard_proc)
        threading.Thread(target=stream_reader, args=(dashboard_proc.stdout, "Dash-Out"), daemon=True).start()

        log("Starting Frontend Cloudflare Tunnel...")
        fe_tunnel_cmd = [CLOUDFLARED_PATH, "tunnel", "--url", f"http://localhost:{DASHBOARD_PORT}"]
        fe_tunnel_proc = subprocess.Popen(fe_tunnel_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        processes.append(fe_tunnel_proc)
        
        fe_url, pipe = find_tunnel_url(fe_tunnel_proc.stderr, "FE-Tunnel")
        if fe_url:
            log(f"✅ Frontend Tunnel established at: {fe_url}")
            
            # Save Frontend URL to Redis so backend can use it for notifications
            try:
                subprocess.run([VENV_PYTHON, "-c", f"import redis; r = redis.Redis(port={REDIS_PORT}); r.set('config:frontend_url', '{fe_url}')"], check=False)
                log(f"Saved Frontend URL to Redis config:config:frontend_url")
            except Exception as e:
                log(f"Failed to save URL to Redis: {e}")

            threading.Thread(target=stream_reader, args=(pipe, "FE-Tunnel"), daemon=True).start()
        else:
            log("Failed to start Frontend Tunnel.")

    # Send URLs to Telegram
    try:
        log("🚀 Sending system URLs to Telegram...")
        msg = f"🚀 <b>System Started</b>\\n\\nFrontend: {fe_url}\\nBackend: {be_url}\\nn8n: {n8n_url}"
        
        # Use VENV_PYTHON to reuse the telegram_bot module
        script = f"import sys; sys.path.append('{os.getcwd()}/backend'); from core.telegram_bot import send_telegram_notification; send_telegram_notification('7508230549', '{msg}', dashboard_link=False)"
        subprocess.run([VENV_PYTHON, "-c", script], check=False)
    except Exception as e:
        log(f"Failed to send Telegram notification: {e}")

    log("🎉 All selected services are running! Press Ctrl+C to stop.")
    
    while True:
        if not processes:
            sys.exit(0)
        for p in processes:
            if p.poll() is not None:
                log(f"Critical process died! Return Code: {p.returncode}")
                cleanup()
        time.sleep(1)

if __name__ == "__main__":
    main()
