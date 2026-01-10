"""
File Router - Endpoints for file operations and command execution.
"""
import os
import subprocess

from fastapi import APIRouter, HTTPException

from core.schemas import FileWriteRequest, CommandRequest

router = APIRouter(tags=["Files & Commands"])


@router.get("/files/list")
def list_files(path: str = "."):
    """List files in a directory."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Path not found")
    return {"files": os.listdir(path)}


@router.post("/files/read")
def read_file(path: str):
    """Read file contents."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    try:
        with open(path, "r") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files/write")
def write_file(request: FileWriteRequest):
    """Write content to a file."""
    try:
        directory = os.path.dirname(request.path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        with open(request.path, "w") as f:
            f.write(request.content)
        return {"status": "success", "path": request.path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/command/run")
def run_command(request: CommandRequest):
    """Execute a shell command."""
    try:
        current_cwd = request.cwd or os.getcwd()
        result = subprocess.run(
            request.command,
            shell=True,
            cwd=current_cwd,
            capture_output=True,
            text=True
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
