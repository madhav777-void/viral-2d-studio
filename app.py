import os
import sys
import pathlib
import urllib.request
import uvicorn

# Set directories
BASE_DIR = pathlib.Path(__file__).resolve().parent
STUDIO_DIR = BASE_DIR / "studio"
SCRIPTS_DIR = BASE_DIR / "cinematic-skill" / "skills" / "cinematic-film" / "scripts"
KOKORO_DIR = BASE_DIR / ".omni-shorts" / "kokoro"
KOKORO_DIR.mkdir(parents=True, exist_ok=True)

# Add to path
sys.path.insert(0, str(STUDIO_DIR))
sys.path.insert(0, str(SCRIPTS_DIR))
os.environ["APP_DIR"] = str(BASE_DIR)
os.environ["OMNI_HOME"] = str(BASE_DIR / ".omni-shorts")

# Ensure Kokoro models exist (download if not present)
model_file = KOKORO_DIR / "kokoro-v1.0.onnx"
voices_file = KOKORO_DIR / "voices-v1.0.bin"

if not model_file.exists():
    print("Downloading Kokoro ONNX model...", flush=True)
    urllib.request.urlretrieve("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx", str(model_file))

if not voices_file.exists():
    print("Downloading Kokoro voices...", flush=True)
    urllib.request.urlretrieve("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin", str(voices_file))

# Import our FastAPI server
from server import app

# Gradio compatibility for Hugging Face Spaces SDK inspection
try:
    import gradio as gr
    demo = gr.mount_gradio_app(app, gr.Blocks(title="Viral 2D Explainer Studio"), path="/gradio")
except Exception:
    demo = None

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting 2D Explainer Studio on port {port}...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port)
