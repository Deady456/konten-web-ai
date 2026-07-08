import re, json, time, subprocess
from pathlib import Path
from urllib.parse import quote
import requests
from .config import CONFIG

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def _search_danbooru(query: str) -> list[str]:
    try:
        tags = quote(query.replace(" ", "_"))
        url = f"https://danbooru.donmai.us/posts.json?tags={tags}+rating:s&limit=5"
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        posts = r.json()
        urls = []
        for p in posts:
            f = p.get("file_url", "")
            if f and "pximg.net" in f:
                urls.append(f)
        for p in posts:
            f = p.get("file_url", "")
            if f and f not in urls:
                urls.append(f)
        return urls[:5]
    except Exception:
        return []

def _search_anilist(query: str) -> list[str]:
    try:
        ql = """
        query($s:String){Page(page:1,perPage:5){
          media(search:$s,type:ANIME){coverImage{large extraLarge}}
          characters(search:$s){image{large}}
        }}"""
        r = requests.post("https://graphql.anilist.co",
            json={"query": ql, "variables": {"s": query}},
            headers={"Content-Type": "application/json"}, timeout=15)
        r.raise_for_status()
        data = r.json().get("data", {}).get("Page", {})
        urls = []
        for m in data.get("media", []):
            ci = m.get("coverImage", {})
            for k in ("extraLarge", "large"):
                if ci.get(k):
                    urls.append(ci[k])
        for c in data.get("characters", []):
            ci = c.get("image", {})
            if ci.get("large"):
                urls.append(ci["large"])
        return urls[:5]
    except Exception:
        return []

def _search_konachan(query: str) -> list[str]:
    try:
        tags = quote(query.replace(" ", "+"))
        url = f"https://konachan.com/post.json?tags={tags}+rating:s&limit=5"
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        posts = r.json()
        urls = []
        for p in posts:
            f = p.get("file_url", "")
            if f:
                urls.append(f)
        return urls[:5]
    except Exception:
        return []

def _search_zerochan(query: str) -> list[str]:
    try:
        url = f"https://www.zerochan.net/{quote(query)}?s=rating"
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        urls = re.findall(r'(https://static\.zerochan\.net/[^"\'\\]+\.(?:jpg|jpeg|png|webp))', r.text)
        return urls[:5]
    except Exception:
        return []

def _search_myanimelist(query: str) -> list[str]:
    try:
        url = f"https://myanimelist.net/anime.php?q={quote(query)}&cat=anime"
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        urls = re.findall(r'(https://cdn\.myanimelist\.net/[^"\'\\]+\.(?:jpg|jpeg|png|webp))', r.text)
        seen = []
        for u in urls:
            if u not in seen and "questionmark" not in u:
                seen.append(u)
        return seen[:5]
    except Exception:
        return []

_SOURCES = [
    ("Danbooru", _search_danbooru),
    ("AniList", _search_anilist),
    ("Konachan", _search_konachan),
    ("Zerochan", _search_zerochan),
    ("MyAnimeList", _search_myanimelist),
]

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

def _ensure_portrait_clip(img_path: Path, out_path: Path, duration: float, w: int, h: int, fps: int):
    frames = int(duration * fps)
    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", str(img_path),
        "-vf",
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"zoompan=z='if(eq(on,1),1,min(1.15,zoom+0.008))':d={frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={w}x{h}:fps={fps}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", f"{duration:.3f}",
        str(out_path),
    ], capture_output=True, text=True)
    return out_path

def _fallback_clip(out_path: Path, duration: float, w: int, h: int, fps: int):
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", f"color=c=#1a1a2e:s={w}x{h}:r={fps}:d={duration:.3f}",
        "-vf", "drawtext=text='Anime Facts':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ], capture_output=True, text=True)

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

        for src_name, src_fn in _SOURCES:
            urls = src_fn(q)
            if urls:
                print(f"      trying {src_name}...")
                for url in urls:
                    if _download(url, out_dir / f"img_{i:02d}.jpg"):
                        img_url = url
                        print(f"      found via {src_name}: {url[:80]}...")
                        break
            if img_url:
                break

        if img_url:
            _ensure_portrait_clip(
                out_dir / f"img_{i:02d}.jpg",
                out_path, scene_dur, w, h, fps,
            )
        else:
            print(f"      no image found, using fallback")
            _fallback_clip(out_path, scene_dur, w, h, fps)

        print(f"      done ({time.time()-t0:.0f}s)")
        paths.append(out_path)
    return paths
