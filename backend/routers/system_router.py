from fastapi import APIRouter
import sys
import os
import subprocess
import threading
import time
from core.logging_config import logger

router = APIRouter(tags=["System"])


def restart_server():
    """Restarts the current python process."""
    logger.info("Restarting server in 2 seconds...")
    time.sleep(2)
    logger.info("Executing restart...")
    python = sys.executable
    os.execl(python, python, *sys.argv)


@router.post("/system/restart")
def trigger_restart():
    """Trigger a self-restart of the server process."""
    logger.warning("System restart requested via API.")
    threading.Thread(target=restart_server).start()
    return {"status": "restarting", "message": "Server is restarting..."}


@router.get("/system/status")
def get_system_status():
    """Get status of backend and n8n services."""
    # Check n8n status
    n8n_running = False
    try:
        result = subprocess.run(["pgrep", "-f", "n8n"], capture_output=True)
        n8n_running = result.returncode == 0
    except:
        pass
    
    return {
        "backend": "running",
        "n8n": "running" if n8n_running else "stopped"
    }


@router.post("/system/n8n/start")
def start_n8n():
    """Start n8n service."""
    try:
        subprocess.Popen(
            ["n8n", "start"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        logger.info("n8n start command issued")
        return {"status": "starting", "message": "n8n is starting..."}
    except Exception as e:
        logger.error(f"Failed to start n8n: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/system/n8n/stop")
def stop_n8n():
    """Stop n8n service."""
    try:
        subprocess.run(["pkill", "-f", "n8n"], capture_output=True)
        logger.info("n8n stop command issued")
        return {"status": "stopped", "message": "n8n stopped"}
    except Exception as e:
        logger.error(f"Failed to stop n8n: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/system/n8n/restart")
def restart_n8n():
    """Restart n8n service."""
    stop_n8n()
    time.sleep(1)
    return start_n8n()
