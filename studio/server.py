import os
import uuid
import threading
from typing import Dict, Any, Optional
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from video_engine import (
    get_available_styles,
    get_available_voices,
    run_pipeline,
    generate_seedance_prompt,
    BASE_DIR
)
from dynamic_ai_engine import run_dynamic_pipeline
from cinematic_director import run_2d_cinematic_pipeline

app = FastAPI(title="Viral Faceless Video Studio")

# Static files for UI
STATIC_DIR = BASE_DIR / "static"
EXPORTS_DIR = BASE_DIR / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# In-memory jobs tracking
jobs: Dict[str, Dict[str, Any]] = {}

class GenerateRequest(BaseModel):
    prompt: str
    engine_mode: str = "cinematic_2d"  # "cinematic_2d" (Skia 2D motion graphics), "dynamic_ai" (AI story visuals), or "code_diorama"
    style: str = "aesthetic_grid"
    aspect: str = "16:9"
    duration: int = 45
    voice: str = "am_michael"
    enable_voiceover: bool = True
    gemini_key: Optional[str] = ""
    openai_key: Optional[str] = ""
    elevenlabs_key: Optional[str] = ""
    elevenlabs_voice_id: Optional[str] = ""

def background_video_task(job_id: str, req: GenerateRequest):
    jobs[job_id]["status"] = "processing"
    
    def on_log(msg: str):
        jobs[job_id]["logs"].append(msg)
        jobs[job_id]["current_step"] = msg

    try:
        # Check if 2D Cinematic Skia Motion Graphics
        if req.engine_mode == "cinematic_2d" or req.style in ["aesthetic_grid", "aesthetic_light", "aesthetic_dark", "studio", "slate", "wall", "blueprint"]:
            look = req.style if req.style in ["aesthetic_grid", "aesthetic_light", "aesthetic_dark", "studio", "slate", "wall", "blueprint"] else "aesthetic_grid"
            res = run_2d_cinematic_pipeline(
                job_id=job_id,
                prompt=req.prompt,
                look=look,
                aspect=req.aspect,
                duration=req.duration,
                voice=req.voice,
                enable_voiceover=req.enable_voiceover,
                gemini_key=req.gemini_key,
                log_callback=on_log
            )
        # If dynamic_ai or style is an AI dynamic style:
        elif req.engine_mode == "dynamic_ai" or req.style in ["2d_story", "cinematic_3d", "photorealistic", "dark_noir", "comic_anime", "tall_tale_2d3d"]:
            res = run_dynamic_pipeline(
                job_id=job_id,
                prompt=req.prompt,
                style_key=req.style,
                aspect=req.aspect,
                duration=req.duration,
                voice=req.voice,
                gemini_key=req.gemini_key,
                log_callback=on_log
            )
        else:
            res = run_pipeline(
                job_id=job_id,
                prompt=req.prompt,
                style=req.style,
                aspect=req.aspect,
                duration=req.duration,
                voice=req.voice,
                gemini_key=req.gemini_key,
                openai_key=req.openai_key,
                elevenlabs_key=req.elevenlabs_key,
                elevenlabs_voice_id=req.elevenlabs_voice_id,
                log_callback=on_log
            )
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = res
    except Exception as e:
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        on_log(f"ERROR: {str(e)}")

@app.get("/api/styles")
def api_styles():
    return {"styles": get_available_styles()}

@app.get("/api/voices")
def api_voices():
    return {"voices": get_available_voices()}

@app.post("/api/generate")
def api_generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {
        "job_id": job_id,
        "prompt": req.prompt,
        "style": req.style,
        "aspect": req.aspect,
        "duration": req.duration,
        "status": "queued",
        "current_step": "Job queued",
        "logs": [],
        "result": None,
        "error": None
    }
    background_tasks.add_task(background_video_task, job_id, req)
    return {"status": "success", "job_id": job_id}

@app.get("/api/status/{job_id}")
def api_status(job_id: str):
    if job_id not in jobs:
        # Check if file exists in exports
        mp4_path = EXPORTS_DIR / f"{job_id}.mp4"
        if mp4_path.exists():
            return {
                "job_id": job_id,
                "status": "completed",
                "result": {"video_file": f"/api/video/{job_id}"}
            }
        raise HTTPException(status_code=404, detail="Job not found")
    return jobs[job_id]

@app.get("/api/video/{job_id}")
def api_video(job_id: str):
    video_path = EXPORTS_DIR / f"{job_id}.mp4"
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not ready or not found")
    return FileResponse(path=str(video_path), media_type="video/mp4", filename=f"{job_id}.mp4")

@app.get("/api/script/{job_id}")
def api_script(job_id: str):
    script_path = EXPORTS_DIR / f"{job_id}_script.txt"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Script text file not found")
    return FileResponse(path=str(script_path), media_type="text/plain; charset=utf-8", filename=f"{job_id}_script.txt")

@app.delete("/api/video/{job_id}")
@app.post("/api/video/{job_id}/delete")
def api_delete_video(job_id: str):
    import shutil
    deleted = False
    mp4_path = EXPORTS_DIR / f"{job_id}.mp4"
    if mp4_path.exists():
        try:
            mp4_path.unlink()
            deleted = True
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to delete video file: {e}")
            
    board_path = EXPORTS_DIR / f"{job_id}_board.jpg"
    if board_path.exists():
        try:
            board_path.unlink()
        except Exception:
            pass

    script_path = EXPORTS_DIR / f"{job_id}_script.txt"
    if script_path.exists():
        try:
            script_path.unlink()
        except Exception:
            pass

    # Clean up project directory if present
    proj_dir = BASE_DIR / "projects" / f"film_{job_id}"
    if proj_dir.exists():
        try:
            shutil.rmtree(proj_dir)
        except Exception:
            pass
            
    if job_id in jobs:
        del jobs[job_id]

    if not deleted:
        raise HTTPException(status_code=404, detail="Video not found")

    return {"status": "success", "message": f"Successfully deleted video {job_id}"}

class SeedanceRequest(BaseModel):
    topic: str
    style: str = "Cinematic B-Roll"
    hook_type: str = "The Visual Metaphor"
    platform: str = "YouTube 16:9"
    duration: int = 8
    sound_priority: str = "narration-first"
    gemini_key: Optional[str] = ""
    openai_key: Optional[str] = ""

@app.post("/api/seedance/generate")
def api_seedance_generate(req: SeedanceRequest):
    data = generate_seedance_prompt(
        topic=req.topic,
        style=req.style,
        hook_type=req.hook_type,
        platform=req.platform,
        duration=req.duration,
        sound_priority=req.sound_priority,
        gemini_key=req.gemini_key or "",
        openai_key=req.openai_key or ""
    )
    return {"status": "success", "data": data}

@app.get("/api/board/{job_id}")
def api_board(job_id: str):
    board_path = EXPORTS_DIR / f"{job_id}_board.jpg"
    if not board_path.exists():
        raise HTTPException(status_code=404, detail="Storyboard not found")
    return FileResponse(path=str(board_path), media_type="image/jpeg")

@app.get("/api/videos")
def api_videos():
    items = []
    for f in EXPORTS_DIR.glob("*.mp4"):
        job_id = f.stem
        meta = jobs.get(job_id, {})
        items.append({
            "job_id": job_id,
            "filename": f.name,
            "title": meta.get("result", {}).get("title") or meta.get("prompt") or job_id,
            "created_time": f.stat().st_mtime,
            "video_url": f"/api/video/{job_id}",
            "board_url": f"/api/board/{job_id}" if (EXPORTS_DIR / f"{job_id}_board.jpg").exists() else None,
            "script_url": f"/api/script/{job_id}" if (EXPORTS_DIR / f"{job_id}_script.txt").exists() else None
        })
    items.sort(key=lambda x: x["created_time"], reverse=True)
    return {"videos": items}

# Mount static folder
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("Starting Studio server on http://localhost:8000 and http://0.0.0.0:8000 ...")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
