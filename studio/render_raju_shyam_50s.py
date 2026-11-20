import os
import sys
from pathlib import Path

from create_50s_raju_shyam import assemble_video

brain_dir = Path(r"C:\Users\Madhav Sharma\.gemini\antigravity\brain\298b3df6-b4f1-4588-86ad-de19beb45bf8")

clips = [
    (brain_dir / "raju_shyam_split_screen_clip_01_1795104018151.jpg", "zoom_in"),
    (brain_dir / "clip2_raju_shyam_salary_1795104060382.jpg", "zoom_in"),
    (brain_dir / "clip3_raju_shyam_tea_stall_1795104069995.jpg", "pan_left"),
    (brain_dir / "clip4_raju_motorcycle_emi_1795104070397.jpg", "zoom_in"),
    (brain_dir / "clip5_raju_riding_motorcycle_1795104103035.jpg", "pan_right"),
    (brain_dir / "clip6_savings_jar_v2_1795104099644.jpg", "zoom_in"),
    (brain_dir / "clip7_sip_savings_jar_1795104087199.jpg", "zoom_in"),
    (brain_dir / "clip8_raju_shyam_split_comparison_1795104106389.jpg", "zoom_out"),
    (brain_dir / "clip_9_raju_cafe_1795104115284.jpg", "zoom_in"),
    (brain_dir / "clip10_shyam_budgeting_1795104114266.jpg", "pan_left"),
]

# Verify all images exist
for idx, (p, m) in enumerate(clips, 1):
    assert p.exists(), f"Missing clip {idx}: {p}"
print("All 10 clip images verified successfully!")

output_video = Path(__file__).resolve().parent / "exports" / "raju_vs_shyam_50s.mp4"
assemble_video(clips, output_video)
print("Finished rendering 50s video!")
