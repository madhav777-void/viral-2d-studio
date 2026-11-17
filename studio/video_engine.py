import os
import sys
import json
import shutil
import subprocess
import requests
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

LOCAL_ENGINE = ROOT_DIR / "omni-shorts-engine"
SYSTEM_ENGINE = Path(r"C:\Users\Madhav Sharma\.gemini\config\skills\omni-shorts")
SKILL_DIR = LOCAL_ENGINE if LOCAL_ENGINE.exists() else SYSTEM_ENGINE

OMNI_HOME = Path(os.environ.get("OMNI_HOME") or (ROOT_DIR / ".omni-shorts"))

if os.name == "nt" and (OMNI_HOME / "venv" / "Scripts" / "python.exe").exists():
    VENV_PYTHON = OMNI_HOME / "venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = Path(sys.executable)

os.environ["OMNI_HOME"] = str(OMNI_HOME)

def get_available_styles():
    return [
        {
            "id": "aesthetic_grid",
            "name": "✨ Clean Aesthetic (Vox / Linear)",
            "description": "Modern minimalist 2D motion graphics with subtle dot-grid canvas, floating pill badges, and dual-ring cards."
        },
        {
            "id": "aesthetic_dark",
            "name": "🌙 Obsidian Dark (Kurzgesagt)",
            "description": "Sleek dark mode canvas with glowing accent cards and neon flow routes."
        },
        {
            "id": "studio",
            "name": "📄 Studio Light Paper",
            "description": "Clean light documentary paper board with crisp typography and subtle shadows."
        },
        {
            "id": "blueprint",
            "name": "📐 Blueprint Drafting",
            "description": "Technical schematic grid with clean flow arrows and connected systems."
        },
        {
            "id": "slate",
            "name": "🕵️ Investigative Slate",
            "description": "Cool slate grey board for deep-dive investigations, loopholes, and business breakdown."
        }
    ]

def get_available_voices():
    return [
        {"id": "am_michael", "name": "Michael (US Male - Steady Explainer)", "type": "free"},
        {"id": "af_heart", "name": "Heart (US Female - Warm & Clear)", "type": "free"},
        {"id": "am_puck", "name": "Puck (US Male - Lively & Energetic)", "type": "free"},
        {"id": "af_bella", "name": "Bella (US Female - Bright & Upbeat)", "type": "free"},
        {"id": "am_fenrir", "name": "Fenrir (US Male - Deep & Authoritative)", "type": "free"},
        {"id": "bm_george", "name": "George (UK Male - Documentary Style)", "type": "free"},
        {"id": "bm_fable", "name": "Fable (UK Male - Storyteller)", "type": "free"},
        {"id": "bf_emma", "name": "Emma (UK Female - Calm & Focused)", "type": "free"},
        {"id": "elevenlabs_custom", "name": "Custom ElevenLabs Voice (Requires API Key)", "type": "elevenlabs"}
    ]

def hydrate_project(style_id: str, project_dir: Path):
    src_example = SKILL_DIR / "styles" / style_id / "example"
    if not src_example.exists():
        raise ValueError(f"Style example not found for {style_id}")

    if project_dir.exists():
        shutil.rmtree(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    # Copy example base files
    shutil.copytree(src_example, project_dir, dirs_exist_ok=True)
    (project_dir / "renders").mkdir(exist_ok=True)
    (project_dir / "review").mkdir(exist_ok=True)
    (project_dir / "data").mkdir(exist_ok=True)

    # Hydrate shared files
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    import shared
    shared.hydrate(style_id, str(project_dir))

    for f in ["narration.wav", "mix.wav", "lines.json", "words.json", "cues.json"]:
        p = project_dir / "data" / f
        if p.exists():
            p.unlink()

def clean_prompt(raw: str) -> str:
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    cleaned = []
    for l in lines:
        if l.lower().startswith("prompt:"):
            cleaned.append(l[7:].strip())
        elif any(k in l.lower() for k in ["best for:", "isme ", "banenge", "animated stick", "recommended settings:"]):
            continue
        else:
            cleaned.append(l)
    res = " ".join(cleaned).strip()
    return res if res else raw

def call_gemini_api(prompt: str, style_name: str, aspect: str, target_seconds: int, api_key: str):
    prompt = clean_prompt(prompt)
    num_cuts = max(14, min(22, int(target_seconds / 3.5)))
    
    instruction = f"""You are an elite viral video director and scriptwriter (like Zack D. Films / Vox / Johnny Harris).
Write a thrilling, high-retention explainer script for:
"{prompt}"

Style: {style_name}
Format: {aspect}
Target duration: ~{target_seconds} seconds

MANDATORY RULES:
1. PUNCHY 2-SECOND HOOK: Start with an impossible fact, loophole, or shocker immediately. Never say 'Hey guys' or 'Today we will discuss'.
2. FAST CUTS: Split the narration into exactly {num_cuts} distinct lines (each line is ONE visual camera cut, lasting 1.5 to 3.5 seconds).
3. STORY ARC: Hook -> Escalation -> Shocking mechanism or rule -> Climax -> Final punchline that loops back.
4. RETURN ONLY PURE JSON matching this exact structure:
{{
  "title": "Short Punchy Title",
  "aspect": "{aspect}",
  "lines": [
    {{ "text": "First punchy hook line.", "caps": "FIRST *PUNCHY | HOOK *LINE." }},
    {{ "text": "Second sentence escalating the situation." }},
    ... ({num_cuts} total lines)
  ]
}}"""

    models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    last_err = None
    for model_name in models:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": instruction}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(url, json=payload, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text)
                if parsed.get("lines") and len(parsed["lines"]) >= 5:
                    return parsed
            else:
                last_err = f"{model_name}: {resp.status_code} {resp.text[:120]}"
        except Exception as e:
            last_err = f"{model_name}: {str(e)}"
            
    raise RuntimeError(f"Gemini API error: {last_err}")

def generate_default_script(prompt: str, aspect: str):
    prompt = clean_prompt(prompt)
    title = prompt[:45] if prompt else "Unbelievable True Story"
    return {
        "title": title,
        "aspect": aspect,
        "lines": [
            {"text": f"In a world where everyone plays by the rules, one story about {prompt} shocked everyone.", "caps": f"THE SHOCKING | TRUTH ABOUT *{prompt.upper()[:25]}"},
            {"text": "Most people thought the system was completely airtight."},
            {"text": "Nobody expected a tiny loophole hidden right in plain sight."},
            {"text": "See, the official guidelines had one crucial mistake."},
            {"text": "And when someone finally tested it, the whole room went dead silent."},
            {"text": "At first, the officials smiled and shook their heads."},
            {"text": "They thought it was just a joke."},
            {"text": "Until they opened the rulebook and checked the fine print."},
            {"text": "Nothing said you couldn't do it."},
            {"text": "Within forty-eight hours, the decision was officially approved."},
            {"text": "And the impossible transaction went straight through the system."},
            {"text": "That's when management realized what happened and started panicking."},
            {"text": "They scrambled to reverse the process before the deadline passed."},
            {"text": "Lawyers were called, documents were reviewed, but it was too late."},
            {"text": "The money and the deal were legally sealed."},
            {"text": "Soon after, emergency regulations were passed to shut it down forever."},
            {"text": "Which is why today, you can never exploit this loophole again.", "caps": "YOU CAN NEVER | EXPLOIT THIS *AGAIN."}
        ]
    }

def run_pipeline(job_id: str, prompt: str, style: str, aspect: str, duration: int, voice: str, 
                 gemini_key: str = "", openai_key: str = "", elevenlabs_key: str = "", 
                 elevenlabs_voice_id: str = "", log_callback=None):
    def log(msg):
        if log_callback:
            log_callback(msg)
        print(f"[{job_id}] {msg}", flush=True)

    log(f"Starting video generation job: '{prompt}' ({aspect}, {style}, {duration}s)")
    proj_dir = BASE_DIR / "projects" / job_id
    exports_dir = BASE_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)

    # Step 1: Hydrate project
    log(f"Setting up {style} diorama engine & assets...")
    hydrate_project(style, proj_dir)

    # Step 2: Generate Script
    log("Crafting viral hook & script with AI...")
    script_data = None
    if gemini_key:
        try:
            log("Calling Google Gemini API with user's key...")
            script_data = call_gemini_api(prompt, style, aspect, duration, gemini_key)
        except Exception as e:
            log(f"Gemini API warning: {e}. Falling back...")
    
    if not script_data and openai_key:
        try:
            log("Calling OpenAI API with user's key...")
            script_data = call_openai_api(prompt, style, aspect, duration, openai_key)
        except Exception as e:
            log(f"OpenAI API warning: {e}. Falling back...")

    if not script_data:
        log("Using intelligent script generator...")
        script_data = generate_default_script(prompt, aspect)

    # Ensure aspects and settings are set
    script_data["aspect"] = aspect
    script_data["voice"] = voice if voice != "elevenlabs_custom" else "am_michael"
    if elevenlabs_key and elevenlabs_voice_id:
        script_data["engine"] = "elevenlabs"
        script_data["voice_id"] = elevenlabs_voice_id
        os.environ["ELEVENLABS_API_KEY"] = elevenlabs_key

    # Save script.json
    with open(proj_dir / "script.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, indent=2)
    log(f"Script ready: '{script_data.get('title')}' ({len(script_data.get('lines', []))} scenes)")

    # Step 3: Generate Voice
    log("Generating natural narration voice...")
    voice_py = SKILL_DIR / "scripts" / "voice.py"
    env = os.environ.copy()
    env["OMNI_HOME"] = str(OMNI_HOME)
    res = subprocess.run([str(VENV_PYTHON), str(voice_py), str(proj_dir)], env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Voice generation failed: {res.stderr or res.stdout}")
    log("Voice audio synthesized successfully.")

    # Step 4: Word-level alignment
    log("Running Whisper auto-sync for word-by-word subtitles...")
    words_py = SKILL_DIR / "scripts" / "words.py"
    res = subprocess.run([str(VENV_PYTHON), str(words_py), str(proj_dir)], env=env, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Whisper alignment failed: {res.stderr or res.stdout}")
    log("Subtitle timing & word sync complete.")

    # Step 5: Sound cues & audio mixing
    log("Mixing Foley sound effects, whooshes, and music...")
    mix_py = proj_dir / "tools" / "mix.py"
    subprocess.run(["node", str(proj_dir / "tools" / "capture.mjs"), "cues"], cwd=str(proj_dir), capture_output=True)
    subprocess.run([str(VENV_PYTHON), str(mix_py), "."], cwd=str(proj_dir), env=env, capture_output=True)

    # Step 6: Render video
    log("Launching Headless Chrome 3D/2D visual rendering engine...")
    render_out = proj_dir / "renders" / "final.mp4"
    render_cmd = ["node", str(proj_dir / "tools" / "capture.mjs"), "video", "renders/final.mp4"]
    proc = subprocess.run(render_cmd, cwd=str(proj_dir), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Visual rendering failed: {proc.stderr or proc.stdout}")

    final_mp4 = exports_dir / f"{job_id}.mp4"
    shutil.copy2(render_out, final_mp4)
    
    # Generate a storyboard snapshot for preview
    board_jpg = exports_dir / f"{job_id}_board.jpg"
    subprocess.run(["node", str(proj_dir / "tools" / "capture.mjs"), "board", str(board_jpg)], cwd=str(proj_dir), env=env, capture_output=True)

    log(f"Render completed successfully! Video saved to {final_mp4.name}")
    return {
        "job_id": job_id,
        "title": script_data.get("title"),
        "aspect": aspect,
        "video_file": f"/api/video/{job_id}",
        "board_file": f"/api/board/{job_id}" if board_jpg.exists() else None
    }


def generate_seedance_prompt(topic: str, style: str = "Cinematic B-Roll", hook_type: str = "The Visual Metaphor", 
                             platform: str = "YouTube 16:9", duration: int = 8, sound_priority: str = "narration-first",
                             gemini_key: str = "", openai_key: str = ""):
    """Generate Seedance 2.0 / Higgsfield Faceless Video Prompts following SKILL.md specs"""
    system_instruction = f"""You are the world's top AI director for faceless video generation (Seedance 2.0 / Higgsfield / Sora / Runway Gen-3 / Kling).
Follow the Three Laws of Faceless Content:
1. Never let the screen rest. Every second needs motion.
2. The first frame is the thumbnail.
3. Lighting is character. State exact color temperature in Kelvin (e.g., 2700K tungsten, 6500K daylight).

Follow these Hard Rules:
- NEVER describe human faces or hands directly holding objects at camera.
- Follow the Seedance 2.0 structure:
  [SCENE DESCRIPTION] — [CAMERA MOVEMENT] — [LIGHTING in Kelvin] — [MOOD/ATMOSPHERE] — [MOTION DETAILS] — [SOUND DIRECTION]
- Hook Type must be: {hook_type}
- Platform: {platform}
- Visual Style: {style}
- Sound Priority: {sound_priority}

Return ONLY valid JSON matching this exact structure:
{{
  "title": "Title",
  "topic": "{topic}",
  "platform": "{platform}",
  "style": "{style}",
  "hook_type": "{hook_type}",
  "sound_priority": "{sound_priority}",
  "hook_frame": "0:00-0:02 description...",
  "scenes": [
    {{
      "timecode": "0:02-0:05",
      "scene_name": "PULL-BACK REVEAL",
      "prompt": "Detailed 4-6 line description...",
      "camera": "Movement description with rate descriptor...",
      "lighting": "Color temp in Kelvin and fixtures...",
      "motion": "Specific element motions...",
      "sound": "Specific SFX and music notes..."
    }},
    {{
      "timecode": "0:05-0:08",
      "scene_name": "CONCEPT ESCALATION",
      "prompt": "Detailed description...",
      "camera": "Movement...",
      "lighting": "Lighting...",
      "motion": "Motion...",
      "sound": "Sound..."
    }}
  ],
  "formatted_prompt": "Complete plain-text copy-pasteable prompt for Seedance / Higgsfield / Sora..."
}}"""

    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent?key={gemini_key}"
            payload = {
                "contents": [{"parts": [{"text": f"Topic: {topic}\nStyle: {style}\nHook: {hook_type}\nPlatform: {platform}\nPlease generate the complete Seedance 2.0 prompt JSON."}]}],
                "generationConfig": {"temperature": 0.7, "responseMimeType": "application/json"}
            }
            resp = requests.post(url, json=payload, timeout=35)
            if resp.status_code == 200:
                txt = resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(txt)
        except Exception as e:
            print("Gemini Seedance generation error:", e)

    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": f"Topic: {topic}"}
                ],
                "response_format": {"type": "json_object"}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=35)
            if resp.status_code == 200:
                txt = resp.json()["choices"][0]["message"]["content"].strip()
                return json.loads(txt)
        except Exception as e:
            print("OpenAI Seedance generation error:", e)

    # Intelligent template generator fallback
    return {
        "title": f"Cinematic Faceless: {topic}",
        "topic": topic,
        "platform": platform,
        "style": style,
        "hook_type": hook_type,
        "sound_priority": sound_priority,
        "hook_frame": f"OPENING HOOK (0:00–0:02): Extreme close-up symbolizing {topic} — shallow depth of field, background blurred into warm bokeh — camera imperceptibly pushes forward at 0.2% per frame.",
        "scenes": [
            {
                "timecode": "0:00-0:03",
                "scene_name": "HOOK & ESTABLISH",
                "prompt": f"Extreme macro visual metaphor for {topic}. A single subject rests on a reflective dark surface — shallow focus, cinematic teal and amber color grade.",
                "camera": "Slow push-in (0.2% per frame) with subtle parallax reveal.",
                "lighting": "Single tungsten key light at 3200K, countered by subtle 6500K rim lighting.",
                "motion": "Particles drift through the light beam, subject reflects subtle environmental shifts.",
                "sound": "Low bass riser swelling at 0:02, ambient room hum."
            },
            {
                "timecode": "0:03-0:08",
                "scene_name": "ESCALATION & REVEAL",
                "prompt": f"Camera pulls back to reveal the full scope of {topic}. Empty architectural environment indicating scale and consequence.",
                "camera": "Slow horizontal drift left along negative space, then settling for 1.5 seconds.",
                "lighting": "Motivated interior practical lamps at 2800K mixing with cold dawn light through windows at 7000K.",
                "motion": "Slow smoke wisps rising, distant light flickering once.",
                "sound": "Cello drone entering on downbeat, muffled distant atmosphere."
            }
        ],
        "formatted_prompt": f"""[SCENE DESCRIPTION]: Cinematic faceless documentary on {topic}. Extreme close-up of a symbolic artifact on dark polished mahogany, pulling back to reveal an expansive deserted environment.
[CAMERA MOVEMENT]: Slow push-in over 3 seconds, transitioning to a wide parallax pull-back reveal at 0.3% frame speed.
[LIGHTING]: 2700K warm practical desk lamp against 6500K twilight window glow, creating high-contrast rim lighting and deep negative shadows.
[MOOD/ATMOSPHERE]: High-tension investigative documentary, 35mm film grain at 15% opacity, shallow depth of field.
[MOTION DETAILS]: Slow dust motes drifting across the light beam, camera never resting, living still with 0.5% drift.
[SOUND DIRECTION]: Narration-first, low cello drone, single decaying piano chord, muted ambient room tone."""
    }
