# 🎬 2D Motion Graphics & Documentary Explainer Studio

A high-performance 2D motion graphics and animated video explainer engine powered by **Google Skia**, **Kokoro Neural TTS**, and **FFmpeg**.

Generates aesthetic Vox / Kurzgesagt / Linear style documentary explainers with floating cards, rolling counters, smooth flow routes, and character scene story visuals.

---

## 🌟 What's New & Upgraded (Latest Release)

1. **🧠 Free AI Storyboard Director ($0 / Zero Key Required)**:
   - Eliminates generic fallback templates. Every prompt (e.g. *"Why planes fly"*, *"Bank Paisa Kaise Banata Hai"*, *"How Coffee Works"*) generates **100% unique, topic-specific scenes, facts, and spoken lines**.
   - Supports Google Gemini API if provided, or defaults to the built-in Free AI Director.

2. **📝 Custom Script & Clip Parser**:
   - Paste your own multi-clip scripts directly into the prompt box (e.g., `Clip 1 - ... Voice-over: ... Visual: ... Clip 2 - ...`).
   - The engine automatically parses your exact scenes, dialogue, and on-screen cards!

3. **🎨 2D Story Visuals Style (Like Raju vs Shyam)**:
   - Generates topic-matched 2D flat vector character illustrations for each scene.
   - Applies smooth cinematic Ken Burns camera moves (`zoom_in`, `zoom_out`, `pan_left`, `pan_right`) with word-synced subtitles.

4. **🎙️ Dual Audio Modes (With / Without Voiceover)**:
   - **With Voiceover**: High-quality offline Kokoro AI voice.
   - **Without Voiceover**: Silent narration track with procedural Foley SFX + instant downloadable `{job_id}_script.txt` with timecodes for creators recording their own voice.

5. **⏱️ Extended Durations (30s to 5 Minutes)**:
   - Up to 300 seconds (5 minutes) for long-form deep-dive documentary explainers.

6. **🗑️ Video Library Delete Management**:
   - 1-click delete with confirmation modal in the Rendered Video Library tab.

7. **🚀 1-Click Google Colab Cloud GPU / CPU**:
   - Open `2d_studio_colab.ipynb` directly in Google Colab for free 12 GB RAM cloud rendering without running a local PC.

---

## 💻 Quick Start (Local Run)

### 1. Requirements:
- Python 3.10, 3.11, or 3.12
- FFmpeg (`winget install Gyan.FFmpeg`)
- Git

### 2. Launch Studio:
Double-click `run_studio.bat` or run:
```cmd
run_studio.bat
```
The studio will automatically set up the virtual environment, install dependencies, and open `http://localhost:8000` in your browser.

---

## ☁️ Cloud / Google Colab Launch

Open the 1-click notebook directly in Google Colab:
👉 **[Open in Google Colab](https://colab.research.google.com/github/madhav777-void/viral-2d-studio/blob/main/2d_studio_colab.ipynb)**

Click the **Play [ ▶ ]** button, and in 30 seconds you will get a live public URL to create videos from any device!
