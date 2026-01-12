"""
File Router - Endpoints for file operations and command execution.
"""
import os
import subprocess
import base64
import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from core.schemas import FileWriteRequest, CommandRequest

router = APIRouter(tags=["Files & Commands"])

# Directory for uploaded images
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ImageUploadRequest(BaseModel):
    """Request model for image upload."""
    images: List[str]  # Base64 encoded images
    

@router.post("/files/upload-images")
def upload_images(request: ImageUploadRequest):
    """
    Upload base64 encoded images and return their URLs.
    
    Args:
        images: List of base64 encoded image strings (with or without data URL prefix)
        
    Returns:
        List of uploaded image URLs
    """
    uploaded_urls = []
    
    for idx, img_data in enumerate(request.images):
        try:
            # Parse data URL if present
            if img_data.startswith("data:"):
                # Format: data:image/png;base64,xxxxx
                header, encoded = img_data.split(",", 1)
                # Extract extension from header
                if "png" in header:
                    ext = "png"
                elif "jpeg" in header or "jpg" in header:
                    ext = "jpg"
                elif "gif" in header:
                    ext = "gif"
                elif "webp" in header:
                    ext = "webp"
                else:
                    ext = "png"
            else:
                encoded = img_data
                ext = "png"
            
            # Decode and save
            image_data = base64.b64decode(encoded)
            filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.{ext}"
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            with open(filepath, "wb") as f:
                f.write(image_data)
            
            # Return relative URL (frontend will need to construct full URL)
            uploaded_urls.append(f"/uploads/{filename}")
            
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to process image {idx}: {str(e)}")
    
    return {
        "status": "success",
        "urls": uploaded_urls
    }


@router.get("/uploads/{filename}")
def get_uploaded_file(filename: str):
    """Serve an uploaded file."""
    from fastapi.responses import FileResponse
    
    filepath = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(filepath)


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
