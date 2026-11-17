import os
import sys
import json
import time
import math
import shutil
import pathlib
import subprocess
from pathlib import Path
import numpy as np
import scipy.signal
from scipy.io import wavfile

# Paths - dynamic for both local Windows and Hugging Face Linux Docker
BASE_DIR = Path(os.environ.get("APP_DIR", Path(__file__).resolve().parent.parent))
STUDIO_DIR = BASE_DIR / "studio"
EXPORTS_DIR = STUDIO_DIR / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
PROJECTS_DIR = STUDIO_DIR / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

SKILL_DIR = BASE_DIR / "cinematic-skill" / "skills" / "cinematic-film"
SCRIPTS_DIR = SKILL_DIR / "scripts"

if (BASE_DIR / ".omni-shorts" / "venv" / "Scripts" / "python.exe").exists():
    VENV_PYTHON = BASE_DIR / ".omni-shorts" / "venv" / "Scripts" / "python.exe"
elif (BASE_DIR / ".omni-shorts" / "venv" / "bin" / "python").exists():
    VENV_PYTHON = BASE_DIR / ".omni-shorts" / "venv" / "bin" / "python"
else:
    VENV_PYTHON = Path(sys.executable)

omni_env = os.environ.get("OMNI_HOME")
KOKORO_DIR = Path(omni_env) / "kokoro" if omni_env else (BASE_DIR / ".omni-shorts" / "kokoro")

# Setup sys.path
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(STUDIO_DIR))

def prompt_gemini_cinematic_story(prompt: str, look: str = "aesthetic_grid", aspect: str = "16:9", duration: int = 45, api_key: str = ""):
    import requests
    target_steps = max(4, min(25, int(duration / 12)))
    min_steps = max(3, target_steps - 1)
    max_steps = target_steps + 2

    system_prompt = f"""You are the world's best 2D motion graphics director for documentary explainers (Vox, Johnny Harris, Kurzgesagt, MagnatesMedia).
Topic: "{prompt}"
Format: {aspect}
Target Video Duration: ~{duration} seconds ({min_steps} to {max_steps} steps)
Visual Style: Modern 2D Motion Graphics (Minimalist Dot-grid Canvas, Floating Pill Badges, Dual-ring Bullet Cards, Flow Arrows, Dynamic Rolling Counters).

Design a brilliant {min_steps} to {max_steps} step 2D explainer video storyboard that thoroughly covers the topic in chronological documentary style.
Each step represents a camera stop on a 2D canvas with clean cards, arrows, and data counters.

Return STRICT JSON ONLY matching this exact schema:
{{
  "title": "CATCHY SHORT TITLE (MAX 4 WORDS)",
  "look": "aesthetic_grid",
  "steps": [
    {{
      "id": 1,
      "spoken": "The opening hook sentence spoken by the narrator.",
      "card_title": "TITLE",
      "card_lines": ["First key takeaway", "Second brief detail"],
      "counter": {{"val": 4000000, "prefix": "$", "suffix": "", "caption": "TOTAL CASH"}},
      "stamp": "LOOPHOLE",
      "highlight_word": "loophole"
    }}
  ]
}}
Rules:
- Keep "steps" between {min_steps} and {max_steps} steps for a comprehensive ~{duration}s explainer.
- "look" should be "aesthetic_grid" (clean minimalist dot grid), "aesthetic_dark" (dark mode), "studio" (light paper), or "blueprint".
- "counter" is optional: set to null if no number to roll up.
- "stamp" is optional: set to null or a 1-word badge like "APPROVED", "EXPLOITED", "VOID", "HEIST".
"""
    if not api_key:
        api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("No Gemini API key provided.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}],
        "generationConfig": {"response_mime_type": "application/json"}
    }
    
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        url2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={api_key}"
        resp = requests.post(url2, json=payload, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned {resp.status_code}: {resp.text[:150]}")
            
    data = resp.json()
    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw)

def fallback_cinematic_story(prompt: str):
    words = prompt.split()
    title = " ".join(words[:4]).upper() if words else "THE EXPLAINER"
    return {
        "title": title,
        "look": "studio",
        "steps": [
            {
                "id": 1,
                "spoken": f"Most people believe the story of {prompt} is just a myth.",
                "card_title": "THE DISCOVERY",
                "card_lines": ["Unchecked fine print", "Zero restrictions"],
                "counter": None,
                "stamp": "LOOPHOLE",
                "highlight_word": "myth"
            },
            {
                "id": 2,
                "spoken": "When the mechanics were finally tested, the loophole went completely viral.",
                "card_title": "THE EXPLOIT",
                "card_lines": ["100% legal transaction", "System cleared"],
                "counter": {"val": 1000000, "prefix": "$", "suffix": "", "caption": "TOTAL VALUE"},
                "stamp": "APPROVED",
                "highlight_word": "tested"
            },
            {
                "id": 3,
                "spoken": "By the time officials realized the glitch, the policy was changed forever.",
                "card_title": "THE AFTERMATH",
                "card_lines": ["Guidelines rewritten", "Loophole permanently closed"],
                "counter": None,
                "stamp": "VOID",
                "highlight_word": "forever"
            }
        ]
    }

def generate_scene_code(story_data: dict, look: str = "aesthetic_grid", aspect: str = "16:9"):
    title = story_data.get("title", "THE EXPLAINER").upper()
    steps = story_data.get("steps", [])
    num_steps = len(steps)
    look_val = "aesthetic_grid" if look in ("studio", "aesthetic_grid", "aesthetic_light", "") else look

    # 4K canvas layout
    code = f'''"""2D Motion Graphics Explainer Scene generated dynamically."""
from engine import BigText, AestheticCard, AestheticCounter, AestheticBadge, Film, PenMark, Route

PALETTE = [
    (99, 102, 241),   # 01 Indigo
    (16, 185, 129),   # 02 Emerald
    (245, 158, 11),   # 03 Amber
    (14, 165, 233),   # 04 Sky Cyan
    (244, 63, 94),    # 05 Rose
    (139, 92, 246),   # 06 Violet
]

CARD_W, CARD_H, GAP = 3200, 1950, 4400
XS = [i * GAP for i in range({num_steps})]
MID = (XS[0] + XS[-1]) / 2 if XS else 0

def build_film(doc):
    L, E, W = doc.L, doc.E, doc.W
    film = Film(doc.duration, fps=30, look="{look_val}")

    # Title - Clean modern typography
    film.add(BigText("{title}", MID, -2400, 680, L(1) - 0.1, font="label", rgb=(15, 23, 42), shadow=False, grunge=False, type_on=0.6))
    film.add(PenMark("underline", MID, -2150, 4800, 40, t_in=L(1) + 0.3, dur=0.5, width=16, rgb=(99, 102, 241)))

'''
    # Add Cards, Routes, Counters, Badges
    for idx, st in enumerate(steps):
        line_num = idx + 1
        card_title = st.get("card_title", f"STEP {line_num}").upper()
        card_lines = json.dumps(st.get("card_lines", []))
        tag = f"STEP {line_num:02d}"
        icon_sym = f"{line_num:02d}"
        col_expr = f"PALETTE[{idx} % len(PALETTE)]"

        code += f'''
    # Step {line_num}: {card_title}
    film.add(AestheticCard(XS[{idx}], 0, CARD_W, CARD_H, L({line_num}) + 0.05, tag="{tag}", title="{card_title}", lines={card_lines}, tag_col={col_expr}, icon_symbol="{icon_sym}"))
'''
        # Route from previous card
        if idx > 0:
            prev_col_expr = f"PALETTE[{(idx-1)} % len(PALETTE)]"
            code += f'''    film.add(Route((XS[{idx-1}] + CARD_W / 2 + 60, 0), (XS[{idx}] - CARD_W / 2 - 60, 0), t_in=L({line_num}) - 0.2, dur=0.5, bend=-0.2, width=20, rgb={prev_col_expr}))
'''
        # Counter if present
        cnt = st.get("counter")
        if cnt and isinstance(cnt, dict):
            val = cnt.get("val", 100)
            prefix = cnt.get("prefix", "")
            suffix = cnt.get("suffix", "")
            cap = cnt.get("caption", "").upper()
            code += f'''    film.add(AestheticCounter(XS[{idx}], 1850, 460, {val}, L({line_num}) + 0.5, dur=1.1, prefix="{prefix}", suffix="{suffix}", caption="{cap}", rgb={col_expr}))
'''
        # Badge if stamp present
        stamp = st.get("stamp")
        if stamp and isinstance(stamp, str):
            code += f'''    film.add(AestheticBadge("{stamp.upper()}", XS[{idx}] + 1050, -650, size=180, rot=-4.0, t_in=L({line_num}) + 0.8, rgb={col_expr}))
'''

    # Camera shots
    code += f'''
    # Camera path: Title -> Cards -> Final wide pull back (uniform clean lighting strength=0.0)
    film.shot(0.0, MID, -2300, 0.48, strength=0.0)
    film.shot(E(1) + 0.2, MID, -1100, 0.32, strength=0.0)
'''
    for idx in range(num_steps):
        line_num = idx + 1
        code += f'''    film.shot(L({line_num}) + 0.35, XS[{idx}], 350, 0.58, strength=0.0)
    film.shot(E({line_num}) - 0.1, XS[{idx}] + 180, 420, 0.55, strength=0.0)
'''
    code += f'''    # Final cinematic pull-back showing full system
    film.shot(L({num_steps}) + 0.8, MID, 0, 0.26, strength=0.0)
    film.shot(film.duration, MID, -100, 0.21, strength=0.0)
    return film
'''
    return code

def run_2d_cinematic_pipeline(job_id: str, prompt: str, look: str = "aesthetic_grid",
                              aspect: str = "16:9", duration: int = 45, voice: str = "am_michael",
                              enable_voiceover: bool = True, gemini_key: str = "", log_callback = None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(f"[{job_id}] {msg}", flush=True)

    proj_dir = PROJECTS_DIR / f"film_{job_id}"
    proj_dir.mkdir(parents=True, exist_ok=True)
    audio_dir = proj_dir / "audio"
    lines_dir = audio_dir / "lines"
    lines_dir.mkdir(parents=True, exist_ok=True)
    out_dir = proj_dir / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    log(f"Starting 2D Cinematic Motion Graphics Engine for '{prompt[:45]}...'")

    # Step 1: AI Storyboard
    log("Directing 2D motion graphics storyboard with Gemini AI...")
    story_data = None
    if gemini_key:
        try:
            story_data = prompt_gemini_cinematic_story(prompt, look, aspect, duration, gemini_key)
            log(f"Generated {len(story_data.get('steps', []))} 2D motion graphic scenes!")
        except Exception as e:
            log(f"Gemini API warning: {e}. Using intelligent fallback...")
    
    if not story_data:
        story_data = fallback_cinematic_story(prompt)

    steps = story_data.get("steps", [])
    title = story_data.get("title", prompt[:30])

    # Save script.json
    script_data = {
        "title": title,
        "takes": [
            {
                "take": f"T{st['id']:02d}",
                "lines": [
                    {
                        "id": st["id"],
                        "text": st["spoken"],
                        "spoken": st["spoken"],
                        "hero": f"card {st.get('card_title', 'STEP')}",
                        "typed": st.get("card_title", ""),
                        "gap_after": 0.8 if st["id"] == len(steps) else 0.5
                    }
                ]
            }
            for st in steps
        ],
        "fact_notes": [f"Explainer video for: {prompt}"]
    }
    (proj_dir / "script.json").write_text(json.dumps(script_data, indent=2))
    (proj_dir / "photos.json").write_text(json.dumps({"grade": "natural", "photos": []}))
    (proj_dir / "map.json").write_text(json.dumps({}))

    # Step 2: Voiceover / Timing Generation
    segments = []
    if enable_voiceover:
        log(f"Synthesizing studio voiceover with Kokoro TTS ({len(steps)} scenes)...")
        import kokoro_onnx
        kokoro_model = KOKORO_DIR / "kokoro-v1.0.onnx"
        kokoro_voices = KOKORO_DIR / "voices-v1.0.bin"
        kokoro = kokoro_onnx.Kokoro(str(kokoro_model), str(kokoro_voices))
        
        for idx, st in enumerate(steps):
            lid = st["id"]
            spoken = st["spoken"]
            log(f"🎙️ Voicing Scene {idx+1}/{len(steps)}: '{spoken[:35]}...'")
            samples, sr = kokoro.create(spoken, voice=voice if voice != "elevenlabs_custom" else "am_michael", speed=1.05)
            out_wav = lines_dir / f"seg{lid:02d}.wav"
            
            # Resample to 48000 Hz int16
            samples_48k = scipy.signal.resample(samples, int(len(samples) * 48000 / sr))
            samples_int16 = (samples_48k * 32767).clip(-32768, 32767).astype(np.int16)
            wavfile.write(str(out_wav), 48000, samples_int16)

            segments.append({
                "id": lid,
                "scene": f"T{lid:02d}",
                "caption": spoken,
                "vo": spoken,
                "gap_after": 0.8 if lid == len(steps) else 0.5
            })
    else:
        log("🎙️ Voiceover disabled: Generating timing track instantly (0.1s)...")
        for idx, st in enumerate(steps):
            lid = st["id"]
            spoken = st["spoken"]
            word_count = len(spoken.split())
            dur_s = max(2.5, word_count * 0.38 + 0.6)
            out_wav = lines_dir / f"seg{lid:02d}.wav"
            silent_samples = np.zeros(int(dur_s * 48000), dtype=np.int16)
            wavfile.write(str(out_wav), 48000, silent_samples)

            segments.append({
                "id": lid,
                "scene": f"T{lid:02d}",
                "caption": spoken,
                "vo": spoken,
                "gap_after": 0.8 if lid == len(steps) else 0.5
            })

    (audio_dir / "segments.json").write_text(json.dumps({"segments": segments}, indent=2))

    # Step 3: Build Narration & Timing
    log("Aligning voice timing & timeline...")
    cmd_build_narr = [str(VENV_PYTHON), str(SCRIPTS_DIR / "build_narration.py"), "--project", str(proj_dir)]
    res_narr = subprocess.run(cmd_build_narr, capture_output=True, text=True)
    if res_narr.returncode != 0:
        log(f"ERROR in narration alignment: {res_narr.stderr}")
        raise RuntimeError(f"build_narration failed: {res_narr.stderr}")

    # Step 4: Generate Scene Code (Skia 2D Canvas)
    log("Generating Skia 2D canvas code (Cards, Arrows, Counters, Stamps)...")
    scene_py = generate_scene_code(story_data, look, aspect)
    (proj_dir / "scene.py").write_text(scene_py, encoding="utf-8")

    # Step 5: Prep Textures & Assets
    log("Preparing procedural board textures...")
    cmd_prep = [str(VENV_PYTHON), str(SCRIPTS_DIR / "prep_assets.py"), "--project", str(proj_dir)]
    res_prep = subprocess.run(cmd_prep, capture_output=True, text=True)
    if res_prep.returncode != 0:
        log(f"ERROR in prep_assets: {res_prep.stderr}")
        raise RuntimeError(f"prep_assets failed: {res_prep.stderr}")

    # Step 6: Render Skia Frames
    log("Rendering 2D motion graphics frame-by-frame with Google Skia...")
    from render import make
    film, r, doc = make(str(proj_dir), "1280x720")
    
    # Render frames directly into FFmpeg
    raw_video = out_dir / "raw_video.mp4"
    cmd_ffmpeg = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{r.W}x{r.H}", "-r", "30",
        "-i", "-",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p", str(raw_video)
    ]
    proc = subprocess.Popen(cmd_ffmpeg, stdin=subprocess.PIPE)

    total_frames = int(film.duration * 30)
    for n in range(total_frames):
        if n % 60 == 0:
            pct = int((n / total_frames) * 100)
            log(f"Rendering frame {n}/{total_frames} ({pct}%)...")
        frame_bytes = r.frame(n).tobytes()
        proc.stdin.write(frame_bytes)
    
    proc.stdin.close()
    proc.wait()
    log("Skia 2D motion graphics rendered successfully!")

    # Step 7: Foley & Sound Effects
    log("Synthesizing procedural Foley sound effects (Stamps, Card Pops, Clicks)...")
    cmd_cues = [str(VENV_PYTHON), str(SCRIPTS_DIR / "render.py"), "--project", str(proj_dir), "--cues"]
    subprocess.run(cmd_cues, capture_output=True)
    
    cmd_sfx = [str(VENV_PYTHON), str(SCRIPTS_DIR / "build_sfx.py"), "--project", str(proj_dir)]
    subprocess.run(cmd_sfx, capture_output=True)

    # Step 8: Audio Mix (Voice + SFX)
    mixed_audio = audio_dir / "mix.m4a"
    narration_m4a = audio_dir / "narration.m4a"
    sfx_wav = audio_dir / "sfx.wav"

    if enable_voiceover:
        log("Mixing narration voice and Foley effects...")
        if sfx_wav.exists():
            cmd_mix = [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(narration_m4a),
                "-i", str(sfx_wav),
                "-filter_complex", "[0:a]volume=1.0[v];[1:a]volume=0.35[s];[v][s]amix=inputs=2:duration=first[a]",
                "-map", "[a]", "-c:a", "aac", "-b:a", "192k", str(mixed_audio)
            ]
            subprocess.run(cmd_mix, capture_output=True)
        else:
            mixed_audio = narration_m4a
    else:
        log("Voiceover disabled: Exporting clean video with Foley sound effects only...")
        if sfx_wav.exists():
            cmd_sfx_only = [
                "ffmpeg", "-y", "-v", "error",
                "-i", str(sfx_wav),
                "-c:a", "aac", "-b:a", "192k", str(mixed_audio)
            ]
            subprocess.run(cmd_sfx_only, capture_output=True)
        else:
            cmd_silent = [
                "ffmpeg", "-y", "-v", "error",
                "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                "-t", f"{film.duration:.2f}",
                "-c:a", "aac", "-b:a", "192k", str(mixed_audio)
            ]
            subprocess.run(cmd_silent, capture_output=True)

    # Step 9: Final Assembly
    final_mp4 = EXPORTS_DIR / f"{job_id}.mp4"
    cmd_final = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(raw_video),
        "-i", str(mixed_audio),
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(final_mp4)
    ]
    subprocess.run(cmd_final, check=True)

    # Save thumbnail still
    board_jpg = EXPORTS_DIR / f"{job_id}_board.jpg"
    thumb_frame = r.frame(total_frames - 30) # Final pull-back frame
    from PIL import Image
    Image.fromarray(thumb_frame).save(board_jpg, quality=90)

    # Step 10: Generate Formatted Narration Script (.txt)
    timing_file = audio_dir / "timing.json"
    timing_data = {}
    if timing_file.exists():
        try:
            timing_data = json.loads(timing_file.read_text())
        except Exception:
            pass

    seg_map = {s["id"]: s for s in timing_data.get("segments", [])}

    txt_lines = [
        "=" * 64,
        f"VIDEO TITLE: {title}",
        f"TOPIC: {prompt}",
        f"TOTAL DURATION: ~{int(film.duration)}s ({len(steps)} Scenes)",
        f"AUDIO MODE: {'With AI Voiceover' if enable_voiceover else 'Without AI Voice (Silent Voice Track / SFX Only)'}",
        "=" * 64,
        "",
        "--- COMPLETE NARRATOR SCRIPT & TIMECODES ---",
        ""
    ]

    for st in steps:
        sid = st["id"]
        c_title = st.get("card_title", f"STEP {sid}").upper()
        spoken = st.get("spoken", "")
        lines = st.get("card_lines", [])
        seg = seg_map.get(sid, {})
        start_t = seg.get("start", 0.0)
        end_t = seg.get("end", 0.0)
        start_str = f"{int(start_t // 60):02d}:{int(start_t % 60):02d}"
        end_str = f"{int(end_t // 60):02d}:{int(end_t % 60):02d}"

        txt_lines.append(f"[SCENE {sid:02d} | {start_str} - {end_str}] {c_title}")
        txt_lines.append(f'SPOKEN NARRATOR SCRIPT:\n"{spoken}"')
        if lines:
            txt_lines.append("ON-SCREEN KEY POINTS:")
            for ln in lines:
                txt_lines.append(f"  • {ln}")
        cnt = st.get("counter")
        if cnt and isinstance(cnt, dict):
            txt_lines.append(f"DATA COUNTER: {cnt.get('prefix','')}{cnt.get('val',0):,}{cnt.get('suffix','')} ({cnt.get('caption','')})")
        stamp = st.get("stamp")
        if stamp:
            txt_lines.append(f"BADGE STAMP: [{stamp.upper()}]")
        txt_lines.append("-" * 64)
        txt_lines.append("")

    script_txt_path = EXPORTS_DIR / f"{job_id}_script.txt"
    script_txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    log(f"2D EXPLAINER COMPLETE! Video: {final_mp4.name} | Script: {script_txt_path.name}")
    return {
        "job_id": job_id,
        "title": title,
        "aspect": aspect,
        "video_file": f"/api/video/{job_id}",
        "board_file": f"/api/board/{job_id}",
        "script_file": f"/api/script/{job_id}",
        "has_voiceover": enable_voiceover
    }
