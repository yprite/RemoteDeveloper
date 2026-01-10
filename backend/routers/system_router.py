from fastapi import APIRouter
import sys
import os
import threading
import time
from core.logging_config import logger

router = APIRouter(tags=["System"])

def restart_server():
    """Restarts the current python process."""
    logger.info("Restarting server in 2 seconds...")
    time.sleep(2)
    logger.info("Executing restart...")
    # Re-execute the current script with the same arguments
    python = sys.executable
    os.execl(python, python, *sys.argv)

@router.post("/system/restart")
def trigger_restart():
    """Trigger a self-restart of the server process."""
    logger.warning("System restart requested via API.")
    # Run restart in a separate thread to allow response to return
    threading.Thread(target=restart_server).start()
    return {"status": "restarting", "message": "Server is restarting..."}
