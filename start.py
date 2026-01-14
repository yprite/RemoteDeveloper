"""
System Startup Script

Starts all components for the RemoteDevelop environment:
1. Kills existing instances
2. Starts webtmux (Web Terminal)
3. Starts Telegram Bridge (Bot + Cloudflare Tunnel)
"""
import os
import time
import subprocess
import signal
import sys
from pathlib import Path

def kill_existing():
    """Kill any running instances."""
    print("🧹 Cleaning up old processes...")
    subprocess.run("pkill -9 -f 'webtmux'", shell=True)
    subprocess.run("pkill -9 -f 'telegram_bridge'", shell=True)
    subprocess.run("pkill -9 -f 'cloudflared'", shell=True)
    time.sleep(1)

def start_webtmux():
    """Start webtmux server."""
    print("🚀 Starting webtmux...")
    webtmux_path = os.path.expanduser("~/.local/bin/webtmux")
    cmd = [
        webtmux_path,
        "-c", "admin:admin123",  # Basic Auth
        "-w",                    # Write permission
        "tmux", "new-session", "-A", "-s", "dev"
    ]
    
    # Run in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    if process.poll() is None:
        print(f"✅ webtmux running (PID: {process.pid})")
        return process
    else:
        print("❌ Failed to start webtmux")
        return None

def start_bridge():
    """Start Telegram bridge."""
    print("🤖 Starting Telegram bridge...")
    cmd = ["uv", "run", "python", "telegram_bridge.py"]
    
    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    return process

def main():
    kill_existing()
    
    # Check env
    if not os.path.exists(".env"):
        print("❌ .env file missing!")
        return

    # Start services
    webtmux = start_webtmux()
    if not webtmux:
        return

    bridge = start_bridge()
    
    print("\n✅ System Operational!")
    print("--------------------------------")
    print("1. Telegram Bot: /start to verify")
    print("2. Webtmux: http://localhost:8080")
    print("--------------------------------")
    
    try:
        bridge.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        webtmux.terminate()
        bridge.terminate()

if __name__ == "__main__":
    main()
