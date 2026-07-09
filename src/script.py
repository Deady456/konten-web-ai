import json
import re
import time
from datetime import datetime
from openai import OpenAI, RateLimitError
from .config import LLM_API_KEYS, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER, CONFIG
from . import state, news_fetcher

_key_idx = 0
_client = OpenAI(api_key=LLM_API_KEYS[_key_idx], base_url=LLM_BASE_URL)

def _call_llm(model, max_tokens, response_format, messages, retries=5):
    global _key_idx, _client
    for attempt in range(retries):
        try:
            return _client.chat.completions.create(
                model=model, max_tokens=max_tokens,
                response_format=response_format, messages=messages,
            )
        except RateLimitError as e:
            if _key_idx < len(LLM_API_KEYS) - 1:
                _key_idx += 1
                _client = OpenAI(api_key=LLM_API_KEYS[_key_idx], base_url=LLM_BASE_URL)
                print(f"  Rate limited, switching to key {_key_idx+1}/{len(LLM_API_KEYS)}")
                continue
            if attempt < retries - 1:
                _wait = 2 ** attempt
                print(f"  Rate limited (retry {attempt+1}/{retries} in {_wait}s): {e}")
                time.sleep(_wait)
            else:
                raise
        except Exception as e:
            if attempt < retries - 1:
                _wait = 2 ** attempt
                print(f"  LLM error (retry {attempt+1}/{retries} in {_wait}s): {e}")
                time.sleep(_wait)
            else:
                raise

def _system_prompt(news_context: str = ""):
    s = CONFIG["script"]
    lang = CONFIG.get("language", "en")
    target_words = int(s["target_seconds"] * s["words_per_second"])

    if lang == "id":
        ts, tw = s["target_seconds"], target_words
        date_str = datetime.now().strftime("%d %B %Y")
        return f"""Anda adalah penulis skrip YouTube Shorts berita anime/manga terkini. Hari ini: {date_str}.

Aturan:
- Skrip {ts} detik. BUAT MINIMAL {tw} kata. Skrip PANJANG, informatif, tidak pendek.
- BUAT 6-7 SCENE. Setiap scene 2 kalimat.
- HOOK: 1 kalimat berita VIRAL terkini. Langsung ke inti.
- WAJIB: gunakan BERITA TERKINI di bawah ini sebagai sumber. JANGAN buat fakta umum/evergreen.
- Berita tersedia:
{news_context}
- Akhiri: CTA subscribe 1 kalimat.
- visual_query: nama anime/karakter SPESIFIK bahasa Inggris.

Aturan KHUSUS judul:
- WAJIB spesifik: sebutkan NAMA ANIME, event, atau angkanya.
- DILARANG: judul generik seperti "Anime Terbaru 2026", "Rekomendasi Anime", "Anime Wajib Tonton", "5 Anime Terbaik", "Anime Terbaru Bulan Ini".
- Contoh judul bagus: "Demon Slayer Infinity Castle Rilis 28 Juli!", "Frieren Season 3 Dikonfirmasi Oktober 2027", "HiAnime Dibredel 7 Operator Ditangkap".
- Judul harus bikin penasaran, bukan sekadar label.

Kembalikan ONLY JSON. Skema:
{{"topic": "slug", "title": "Judul max 95 chars", "description": "3-4 kalimat + 5-8 hashtag", "tags": ["10-15 tag"], "scenes": [{{"text": "kalimat narasi", "visual_query": "nama anime spesifik"}}]}}"""
    else:
        return f"""You write viral YouTube Shorts scripts about latest anime/manga news. Today: {datetime.now().strftime('%B %d, %Y')}.

Hard rules:
- The script must run ~{target_seconds} seconds spoken at ~{target_words} words total.
- Start with a strong 1-sentence HOOK about breaking anime news.
- MUST use the CURRENT NEWS below as source. DO NOT write evergreen/generic facts.
- Current news:
{news_context}
- End with a 1-sentence CTA.
- Each scene's visual_query is 2-4 English nouns.

Title rules:
- MUST name the specific anime/manga/event. NO generic titles.
- BANNED: "New Anime 2026", "Best Anime", "Anime You Must Watch", "Top 10 Anime", "New Anime This Month".
- Good examples: "Demon Slayer Infinity Castle Drops July 28", "Frieren Season 3 Confirmed for 2027", "HiAnime Shut Down - 7 Operators Arrested".

Return ONLY valid JSON. Schema:
{{"topic": "short slug", "title": "title max 95 chars, min 40 chars, curiosity-driven and engaging", "description": "3-4 sentences with 5-8 relevant hashtags", "tags": ["10-15 lowercase relevant tags"], "scenes": [{{"text": "spoken sentence", "visual_query": "nouns"}}]}}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"    JSON parse error: {e}")
        print(f"    Raw response (first 500 chars): {text[:500]}")
        raise


def generate():
    lang = CONFIG.get("language", "en")

    print("    fetching current anime news...")
    t_news = time.time()
    news_items = news_fetcher.fetch_headlines(lang=lang)
    news_context = news_fetcher.format_news(news_items)
    print(f"    got {len(news_items)} headlines in {time.time()-t_news:.1f}s")
    for h in news_items[:5]:
        print(f"      - {h['title']}")

    s = state.load()
    used = s.get("used_topics", [])
    used_str = ", ".join(used[-30:]) if used else "(none yet)"

    if lang == "id":
        user_msg = (
            f"Niche: {CONFIG['niche']}\n"
            f"Audience: {CONFIG['audience']}\n"
            f"Topik yang sudah pernah dibuat: {used_str}\n"
            f"Buat SATU Short berdasarkan BERITA TERKINI di atas. DILARANG menggunakan topik yang sudah pernah dibuat. Judul dan isi harus orisinal dan tidak mirip dengan yang sudah ada."
        )
    else:
        user_msg = (
            f"Niche: {CONFIG['niche']}\n"
            f"Audience: {CONFIG['audience']}\n"
            f"Previously used topics: {used_str}\n"
            f"Generate ONE Short based on the CURRENT NEWS above. DO NOT use any previously used topics."
        )

    print(f"    calling {LLM_PROVIDER}/{LLM_MODEL}...")
    t0 = time.time()
    resp = _call_llm(
        model=LLM_MODEL,
        max_tokens=2000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _system_prompt(news_context)},
            {"role": "user", "content": user_msg},
        ],
    )
    raw = resp.choices[0].message.content
    print(f"    LLM responded in {time.time()-t0:.1f}s ({len(raw)} chars)")
    data = _extract_json(raw)

    # Validate each scene has visual_query
    for i, s in enumerate(data["scenes"]):
        if "visual_query" not in s or not s["visual_query"]:
            words = re.findall(r"[a-zA-Z]{3,}", s.get("text", ""))
            fallback = " ".join(words[-3:]) if len(words) >= 3 else "abstract background"
            print(f"    scene {i}: missing visual_query, using \"{fallback}\"")
            s["visual_query"] = fallback

    data["full_text"] = " ".join(s["text"] for s in data["scenes"])

    # Fix generic titles
    title = data.get("title", "")
    generic_patterns = [
        r"^(anime|manga)\s+(terbaru|terbaik|wajib|viral|populer|recommended| baru)",
        r"^(rekomendasi|recommendation)",
        r"^(5|10|7|3|8)\s+(anime|manga|film|rekomendasi)",
        r"^(anime|manga)\s+(terbaru|terbaik)\s+\d{4}",
        r"^wajib (tonton|nonton|lihat)",
        r"^baru di (tonton|nonton)",
    ]
    if any(re.search(p, title.lower()) for p in generic_patterns):
        first_scene_text = data["scenes"][0]["text"] if data["scenes"] else ""
        words = first_scene_text.split()
        # Find specific anime name (proper nouns, capitalized)
        anime_names = [w for w in words if w[0].isupper() and len(w) > 2][:3]
        if anime_names:
            specific = " ".join(anime_names)
            if specific not in title:
                data["title"] = f"{specific}: {title}"[:95]
                print(f"    title fixed: \"{title}\" -> \"{data['title']}\"")

    s_cfg = CONFIG["script"]
    target_words = int(s_cfg["target_seconds"] * s_cfg["words_per_second"])
    min_words = int(target_words * 0.75)
    wc = len(data["full_text"].split())
    if wc < min_words:
        print(f"    WARNING: script too short ({wc} words, need {min_words}), retrying...")
        print(f"    calling {LLM_PROVIDER}/{LLM_MODEL}...")
        t0 = time.time()
        shorter_msg = (
            f"SKRIP SEBELUMNYA TERLALU PENDEK: hanya {wc} kata, minimum {min_words} kata. "
            f"Buat ulang dengan LEBIH PANJANG. Tambah detail berita, tambah scene, tambah kalimat per scene. "
            f"JANGAN BUAT SKRIP PENDEK. Minimal {min_words} kata."
        )
        resp = _call_llm(
            model=LLM_MODEL,
            max_tokens=2000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt(news_context)},
                {"role": "user", "content": user_msg},
                {"role": "assistant", "content": f"{{...}} (only {wc} words)"},
                {"role": "user", "content": shorter_msg},
            ],
        )
        raw = resp.choices[0].message.content
        print(f"    LLM responded in {time.time()-t0:.1f}s ({len(raw)} chars)")
        data = _extract_json(raw)
        for i, s in enumerate(data["scenes"]):
            if "visual_query" not in s or not s["visual_query"]:
                words = re.findall(r"[a-zA-Z]{3,}", s.get("text", ""))
                fallback = " ".join(words[-3:]) if len(words) >= 3 else "abstract background"
                s["visual_query"] = fallback
        data["full_text"] = " ".join(s["text"] for s in data["scenes"])
        wc = len(data["full_text"].split())
        if wc < min_words:
            print(f"    WARNING: retry masih pendek ({wc} words), lanjut aja")
    
    return data
