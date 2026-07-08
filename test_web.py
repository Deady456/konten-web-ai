import sys, shutil
from pathlib import Path
from src import script
from src.config import OUTPUT_DIR
from src.visuals_web import fetch_for_scenes

data = script.generate()
print("TOPIC:", data["topic"])
print("TITLE:", data["title"])
print("SCENES:", len(data["scenes"]))
for i, s in enumerate(data["scenes"]):
    print(f'  {i+1}. "{s["text"]}"')
    print(f'     visual_query: {s["visual_query"]}')

out_dir = OUTPUT_DIR / "_web_test"
if out_dir.exists():
    shutil.rmtree(out_dir)

print()
print("=== FETCHING WEB VISUALS ===")
clips = fetch_for_scenes(data["scenes"], out_dir)
print()
for p in clips:
    kb = p.stat().st_size / 1024
    print(f"  {p.name}: {kb:.0f} KB")
