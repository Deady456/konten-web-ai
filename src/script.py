import json
import re
import time
from datetime import datetime
from openai import OpenAI, RateLimitError
from .config import LLM_API_KEYS, LLM_BASE_URL, LLM_MODEL, LLM_PROVIDER, CONFIG
from . import state, news_fetcher

_key_idx = 0
_client = OpenAI(api_key=LLM_API_KEYS[_key_idx], base_url=LLM_BASE_URL)

# ============================================================
# Format-specific prompts
# ============================================================

FORMAT_PROMPTS = {
    "news_breakdown": (
        "Format: NEWS BREAKDOWN - Analisis berita terkini secara mendalam. "
        "Jelaskan 5W1H (apa, siapa, kapan, di mana, mengapa, bagaimana). "
        "Tambahkan dampak dan reaksi komunitas."
    ),
    "list": (
        "Format: LIST - Berikan fakta-fakta dalam format daftar numerik (1., 2., 3., dst). "
        "Setiap fakta harus singkat, memukau, dan berbeda satu sama lain."
    ),
    "story": (
        "Format: STORY - Ceritakan fakta sebagai mini story/kisah pendek yang engaging. "
        "Buat seolah-olah menceritakan sebuah petualangan atau drama."
    ),
    "deep_dive": (
        "Format: DEEP DIVE - Analisis mendalam satu topik spesifik. "
        "Jelaskan sejarah, fakta tersembunyi, dan mengapa topik ini menarik."
    ),
}


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


def _system_prompt(news_context: str = "", content_format: str = ""):
    s = CONFIG["script"]
    lang = CONFIG.get("language", "en")
    target_words = int(s["target_seconds"] * s["words_per_second"])

    format_instruction = ""
    if content_format and content_format in FORMAT_PROMPTS:
        format_instruction = f"\n\n{FORMAT_PROMPTS[content_format]}"

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

VARIASI TOPIK - Pilih topik yang BERAGAM. Jangan selalu berita yang sama. Variasikan antara:
- Review/premiere anime baru
- Fakta unik anime/manga
- Sejarah anime/manga
- Behind-the-scenes (studio, voice actor, production)
- Rekor penjualan/prestasi
- Drama/kontroversi industry
- Rekomendasi analitis
- Kolaborasi/brand anime
JANGAN ulangi topik yang sudah ada di used_topics. Pilih yang BENAR-BENAR BERBEDA.

Aturan KHUSUS judul:
- WAJIB spesifik: sebutkan NAMA ANIME, event, atau angkanya.
- DILARANG: judul generik seperti "Anime Terbaru 2026", "Rekomendasi Anime", "Anime Wajib Tonton", "5 Anime Terbaik", "Anime Terbaru Bulan Ini".
- Contoh judul bagus: "Demon Slayer Infinity Castle Rilis 28 Juli!", "Frieren Season 3 Dikonfirmasi Oktober 2027", "HiAnime Dibredel 7 Operator Ditangkap".
- Judul harus bikin penasaran, bukan sekadar label.{format_instruction}

Kembalikan ONLY JSON. Skema:
{{"topic": "slug", "title": "Judul max 95 chars", "thumbnail_text": "Teks super pendek (3-5 kata, HURUF KAPITAL) untuk ditampilkan besar di layar 3 detik pertama sebagai hook/thumbnail", "description": "3-4 kalimat + 5-8 hashtag", "tags": ["10-15 tag"], "scenes": [{{"text": "kalimat narasi", "visual_query": "nama anime spesifik"}}]}}"""
    else:
        return f"""You write viral YouTube Shorts scripts about latest anime/manga news. Today: {datetime.now().strftime('%B %d, %Y')}.

Hard rules:
- The script must run ~{s['target_seconds']} seconds spoken at ~{target_words} words total.
- Start with a strong 1-sentence HOOK about breaking anime news.
- MUST use the CURRENT NEWS below as source. DO NOT write evergreen/generic facts.
- Current news:
{news_context}
- End with a 1-sentence CTA.
- Each scene's visual_query is 2-4 English nouns.

TOPIC VARIETY - Choose DIVERSE topics. Don't always cover the same type. Vary between:
- Anime reviews/premieres
- Unique anime/manga facts
- Anime/manga history
- Behind-the-scenes (studios, voice actors, production)
- Sales records/achievements
- Industry drama/controversies
- Analytical recommendations
- Anime brand collaborations
DO NOT repeat topics from used_topics. Pick something COMPLETELY DIFFERENT.

Title rules:
- MUST name the specific anime/manga/event. NO generic titles.
- BANNED: "New Anime 2026", "Best Anime", "Anime You Must Watch", "Top 10 Anime", "New Anime This Month".
- Good examples: "Demon Slayer Infinity Castle Drops July 28", "Frieren Season 3 Confirmed for 2027", "HiAnime Shut Down - 7 Operators Arrested".
{format_instruction}

Return ONLY valid JSON. Schema:
{{"topic": "short slug", "title": "title max 95 chars, min 40 chars, curiosity-driven and engaging", "thumbnail_text": "Very short text (3-5 words, ALL CAPS) to display large on screen for the first 3 seconds as a hook/thumbnail", "description": "3-4 sentences with 5-8 relevant hashtags", "tags": ["10-15 lowercase relevant tags"], "scenes": [{{"text": "spoken sentence", "visual_query": "nouns"}}]}}"""


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


def _is_duplicate_title(title: str, published: list) -> bool:
    tl = title.strip().lower()
    if not tl:
        return False
    for p in published:
        pt = p.get("title", "").strip().lower()
        if not pt:
            continue
        if tl == pt:
            return True
        twords, pwords = tl.split(), pt.split()
        if len(twords) >= 3 and len(pwords) >= 3:
            common = len(set(twords) & set(pwords))
            if common >= min(len(twords), len(pwords)) * 0.8:
                return True
    return False


def _is_duplicate_topic(topic: str, used_topics: list) -> bool:
    """Check if topic slug overlaps with any previously used topic."""
    topic_lower = topic.lower().strip()
    if not topic_lower:
        return False
    for used in used_topics:
        used_lower = used.lower().strip()
        # Exact match
        if topic_lower == used_lower:
            return True
        # Word overlap check (e.g. "solo-leveling-season-3" vs "solo-leveling-karma")
        t_words = set(topic_lower.split("-"))
        u_words = set(used_lower.split("-"))
        if len(t_words) >= 2 and len(u_words) >= 2:
            common = len(t_words & u_words)
            if common >= min(len(t_words), len(u_words)) * 0.6:
                return True
    return False


def generate(content_format: str = None) -> dict:
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
    published = s.get("published", [])

    format_desc = ""
    if content_format and content_format in FORMAT_PROMPTS:
        format_desc = f"\nFormat: {FORMAT_PROMPTS[content_format]}"

    if lang == "id":
        base_msg = (
            f"Niche: {CONFIG['niche']}\n"
            f"Audience: {CONFIG['audience']}\n"
            f"Topik yang sudah pernah dibuat: {used_str}\n"
            f"Buat SATU Short berdasarkan BERITA TERKINI di atas. "
            f"DILARANG menggunakan topik yang sudah pernah dibuat. "
            f"Judul dan isi harus orisinal dan tidak mirip dengan yang sudah ada. "
            f"Topik harus BERAGAM - jangan selalu berita yang sama.{format_desc}"
        )
    else:
        base_msg = (
            f"Niche: {CONFIG['niche']}\n"
            f"Audience: {CONFIG['audience']}\n"
            f"Previously used topics: {used_str}\n"
            f"Generate ONE Short based on the CURRENT NEWS above. "
            f"DO NOT use any previously used topics. "
            f"Title and content must be original and not similar to what has been done before. "
            f"Topics must be DIVERSE - don't always cover the same type.{format_desc}"
        )

    s_cfg = CONFIG["script"]
    target_words = int(s_cfg["target_seconds"] * s_cfg["words_per_second"])
    min_words = int(target_words * 0.75)

    for attempt in range(4):
        user_msg = base_msg
        if attempt > 0:
            user_msg += "\n\nPERINGATAN: topik/judul sebelumnya sudah ada. BUAT YANG BENAR-BENAR BERBEDA dan belum pernah dipublikasikan."

        print(f"    calling {LLM_PROVIDER}/{LLM_MODEL} (attempt {attempt+1}, format: {content_format or 'default'})...")
        t0 = time.time()
        resp = _call_llm(
            model=LLM_MODEL,
            max_tokens=2000,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _system_prompt(news_context, content_format or "")},
                {"role": "user", "content": user_msg},
            ],
        )
        raw = resp.choices[0].message.content
        print(f"    LLM responded in {time.time()-t0:.1f}s ({len(raw)} chars)")
        data = _extract_json(raw)

        hook_text = data.get("thumbnail_text", "").strip()
        if hook_text and data.get("scenes"):
            first_vq = data["scenes"][0].get("visual_query", "abstract background")
            data["scenes"].insert(0, {"text": hook_text, "visual_query": first_vq})

        for i, sc in enumerate(data["scenes"]):
            if "visual_query" not in sc or not sc["visual_query"]:
                words = re.findall(r"[a-zA-Z]{3,}", sc.get("text", ""))
                fallback = " ".join(words[-3:]) if len(words) >= 3 else "abstract background"
                print(f"    scene {i}: missing visual_query, using \"{fallback}\"")
                sc["visual_query"] = fallback

        data["full_text"] = " ".join(sc["text"] for sc in data["scenes"])

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
            first_scene = data["scenes"][0]["text"] if data["scenes"] else ""
            sw = first_scene.split()
            anime_names = [w for w in sw if w[0].isupper() and len(w) > 2][:3]
            if anime_names:
                specific = " ".join(anime_names)
                if specific not in title:
                    data["title"] = f"{specific}: {title}"[:95]
                    print(f"    title fixed: \"{title}\" -> \"{data['title']}\"")

        wc = len(data["full_text"].split())
        if wc < min_words:
            print(f"    WARNING: script too short ({wc} words, need {min_words}), retrying...")
            continue

        title = data.get("title", "")
        if _is_duplicate_title(title, published):
            print(f"    DUPLICATE TITLE: already published, retrying...")
            continue

        topic = data.get("topic", "")
        if _is_duplicate_topic(topic, used):
            print(f"    DUPLICATE TOPIC: '{topic}' already used, retrying...")
            continue

        data["format"] = content_format
        print(f"    title: {data['title']}")
        return data

    print("    WARNING: could not generate unique/long enough script after 4 attempts, publishing anyway")
    return data
