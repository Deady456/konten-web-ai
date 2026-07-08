import re
import time
import requests
from pathlib import Path
from .config import CONFIG

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

_ANIME_SOURCES = [
    "https://myanimelist.net/anime.php?q={q}",
    "https://anilist.co/search/anime?search={q}",
    "https://wall.alphacoders.com/search.php?search={q}",
]

def _search_google_images(query: str, max_retries: int = 2) -> list[str]:
    for attempt in range(max_retries):
        try:
            search_url = f"https://www.google.com/search?tbm=isch&q={requests.utils.quote(query)}+anime&hl=id"
            r = requests.get(search_url, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            urls = re.findall(r'"(https://[^"]+\.(?:jpg|jpeg|png|webp))"', r.text)
            seen = set()
            clean = []
            for u in urls:
                if any(x in u for x in ("gstatic", "google", "favicon", "logo")):
                    continue
                if u not in seen:
                    seen.add(u)
                    clean.append(u)
            if clean:
                return clean
        except Exception:
            time.sleep(1)
    return []

def _search_myanimelist(query: str) -> list[str]:
    try:
        search_url = f"https://myanimelist.net/anime.php?q={requests.utils.quote(query)}&cat=anime"
        r = requests.get(search_url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        urls = re.findall(r'data-src="(https://cdn\.myanimelist\.net[^"]+\.(?:jpg|jpeg|png|webp))"', r.text)
        return urls[:5]
    except Exception:
        return []

def _search_anime_news_network(query: str) -> list[str]:
    try:
        search_url = f"https://www.animenewsnetwork.com/search?q={requests.utils.quote(query)}"
        r = requests.get(search_url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        urls = re.findall(r'(https://www\.animenewsnetwork\.com/images/[^"\'\\]+\.(?:jpg|jpeg|png|webp))', r.text)
        return urls[:5]
    except Exception:
        return []

def _search_wallpaper(query: str) -> list[str]:
    try:
        search_url = f"https://wall.alphacoders.com/search.php?search={requests.utils.quote(query)}"
        r = requests.get(search_url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        urls = re.findall(r'(https://initia\.alphacoders\.com[^"\'\\]+\.(?:jpg|jpeg|png|webp))', r.text)
        return urls[:5]
    except Exception:
        return []

def _download(url: str, out_path: Path) -> bool:
    try:
        with requests.get(url, headers=_HEADERS, stream=True, timeout=30) as r:
            r.raise_for_status()
            if len(r.content) < 2000:
                return False
            out_path.write_bytes(r.content)
            return True
    except Exception:
        return False

def _image_to_clip(img_path: Path, out_path: Path, duration: float, w: int, h: int, fps: int):
    import subprocess
    frames = int(duration * fps)
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
        "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='if(eq(on,1),1,min(1.2,zoom+0.01))':d={frames}:s={w}x{h}:fps={fps}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True)
    return out_path

def _fallback_clip(out_path: Path, duration: float, w: int, h: int, fps: int):
    import subprocess
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=#1a1a2e:s={w}x{h}:r={fps}:d={duration:.3f}",
        "-vf", f"drawtext=text='Anime Facts':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True)

def fetch_for_scenes(scenes: list[dict], out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    v = CONFIG["video"]
    w, h, fps = v["width"], v["height"], v["fps"]

    for i, scene in enumerate(scenes):
        q = scene["visual_query"]
        scene_dur = scene.get("duration", 5.0)
        out_path = out_dir / f"scene_{i:02d}.mp4"
        print(f"    scene {i+1}/{len(scenes)}: \"{q}\"")

        t0 = time.time()
        img_url = None

        all_urls = _search_google_images(q)
        if not all_urls:
            all_urls = _search_myanimelist(q)
        if not all_urls:
            all_urls = _search_anime_news_network(q)
        if not all_urls:
            all_urls = _search_wallpaper(q)

        for url in all_urls:
            if _download(url, out_dir / f"img_{i:02d}.jpg"):
                img_url = url
                print(f"      found: {url[:80]}...")
                break

        if img_url:
            _image_to_clip(
                out_dir / f"img_{i:02d}.jpg",
                out_path, scene_dur, w, h, fps,
            )
        else:
            print(f"      no image found, using fallback")
            _fallback_clip(out_path, scene_dur, w, h, fps)

        print(f"      done ({time.time()-t0:.0f}s)")
        paths.append(out_path)
    return paths
