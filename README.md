# konten-web-ai

**Pipeline FreeFaceless untuk konten Fakta Anime & Manga — dengan visual dari web scraping + AI generation.**

```
script (Groq) → voiceover (edge-tts) → captions (faster-whisper, local)
  → visual (web scrape / Pollinations AI) → assemble (ffmpeg) → upload (YouTube Data API)
```

Output: 1080×1920, 30fps, ~60 detik Short dengan fakta anime/manga.

## Kenapa berbeda

| | konten-web-ai | FreeFaceless biasa |
|---|---|---|
| Niche | Anime & Manga | Umum |
| Visual | Web scraping (Gambar real) + AI (Pollinations) | Pexels stock video |
| Kombinasi | Acak hybrid (50% web, 50% AI) atau pilih manual | Satu sumber |

## Quickstart (Windows)

Butuh: **Python 3.11+**, **ffmpeg**, **Google account dengan YouTube channel**.

```powershell
# 1. Isi API keys
Copy-Item .env.example .env   # edit .env (Groq key)

# 2. Install dependencies
.\setup.ps1

# 3. Authorize YouTube (buka browser)
.\.venv\Scripts\python -m src.authorize

# 4. Dry run — bikin video aja (gak upload)
.\.venv\Scripts\python -m src.pipeline_hybrid --no-upload

# 5. Real run — bikin + upload
.\.venv\Scripts\python -m src.pipeline_hybrid

# 6. Pilih sumber visual
.\.venv\Scripts\python -m src.pipeline_hybrid --source web   # pake web scrape aja
.\.venv\Scripts\python -m src.pipeline_hybrid --source ai    # pake AI aja
.\.venv\Scripts\python -m src.pipeline_hybrid --source hybrid # campur (default)
```

## Konfigurasi

Edit `config.yaml`:

```yaml
niche: "fakta unik anime & manga..."
visuals:
  source: hybrid       # "web", "ai", atau "hybrid"
  hybrid_mix: 0.5       # 0.0 = semua AI, 1.0 = semua web
```

## Cara kerja

| Stage | File | Fungsi |
|---|---|---|
| 1. Script | `src/script.py` | Groq nulis script fakta anime JSON |
| 2. Voice | `src/voice.py` | edge-tts voiceover bahasa Indonesia |
| 3. Captions | `src/captions.py` | faster-whisper transkrip + caption karaoke |
| 4a. Web visual | `src/visuals_web.py` | Scrape gambar dari Google Images, MyAnimeList, AnimeNewsNetwork, Wallpaper |
| 4b. AI visual | `src/visuals_ai.py` | Generate gambar via Pollinations.ai dengan gaya anime |
| 5. Assemble | `src/assemble_ai.py` | ffmpeg slideshow + Ken Burns zoom |
| 6. Upload | `src/upload.py` | YouTube Data API v3 |
| Orchestrator | `src/pipeline_hybrid.py` | Jalanin 1-6 dengan kombinasi web + AI |

## License

**MIT** — see [LICENSE](LICENSE).
