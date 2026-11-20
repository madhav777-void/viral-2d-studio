import os
import sys
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "projects" / "raju_vs_shyam"
CLIPS_DIR = PROJECTS_DIR / "clips"
EXPORTS_DIR = BASE_DIR / "exports"

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

W, H = 1280, 720
FPS = 30
DURATION_PER_CLIP = 5.0
TOTAL_FRAMES = int(DURATION_PER_CLIP * FPS) # 150 frames

MOTIONS = {
    "zoom_in": f"scale={W}:{H},zoompan=z='min(zoom+0.0015,1.22)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={TOTAL_FRAMES}:s={W}x{H}:fps={FPS}",
    "zoom_out": f"scale={W}:{H},zoompan=z='max(1.22-0.0015*on,1.0)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={TOTAL_FRAMES}:s={W}x{H}:fps={FPS}",
    "pan_left": f"scale={W}:{H},zoompan=z='1.12':x='x+1.2':y='ih/2-(ih/zoom/2)':d={TOTAL_FRAMES}:s={W}x{H}:fps={FPS}",
    "pan_right": f"scale={W}:{H},zoompan=z='1.12':x='max(0,x-1.2)':y='ih/2-(ih/zoom/2)':d={TOTAL_FRAMES}:s={W}x{H}:fps={FPS}"
}

def render_clip(img_path: Path, motion: str, out_clip: Path):
    filter_expr = MOTIONS.get(motion, MOTIONS["zoom_in"])
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
        "-vf", filter_expr,
        "-c:v", "libx264", "-t", f"{DURATION_PER_CLIP}",
        "-pix_fmt", "yuv420p", "-r", f"{FPS}", str(out_clip)
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def assemble_video(image_motion_pairs, final_output: Path):
    clip_files = []
    for idx, (img_path, motion) in enumerate(image_motion_pairs):
        clip_path = CLIPS_DIR / f"clip_{idx+1:02d}.mp4"
        print(f"Rendering Clip {idx+1}/{len(image_motion_pairs)} ({motion})...")
        render_clip(Path(img_path), motion, clip_path)
        clip_files.append(clip_path)

    concat_txt = PROJECTS_DIR / "concat.txt"
    with open(concat_txt, "w", encoding="utf-8") as f:
        for c in clip_files:
            f.write(f"file '{c.resolve().as_posix()}'\n")

    temp_video = PROJECTS_DIR / "video_no_audio.mp4"
    cmd_concat = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_txt),
        "-c", "copy", str(temp_video)
    ]
    subprocess.run(cmd_concat, check=True, capture_output=True)

    # Add gentle ambient explainer soundtrack / audio
    cmd_audio = [
        "ffmpeg", "-y",
        "-i", str(temp_video),
        "-f", "lavfi", "-i", f"sine=frequency=220:duration=50",
        "-af", "volume=0.0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        str(final_output)
    ]
    subprocess.run(cmd_audio, check=True, capture_output=True)
    print(f"SUCCESS! 50-Second Video created: {final_output}")

if __name__ == "__main__":
    print("Assembler ready.")
