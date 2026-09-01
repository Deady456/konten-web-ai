import re

ALGOSPEAK_MAP = {
    r'\bm4t1\b': 'mati',
    r'\bm4ti\b': 'mati',
    r'\bmat1\b': 'mati',
    r'\bny4w4\b': 'nyawa',
    r'\bny4wa\b': 'nyawa',
    r'\btr4g3d1\b': 'tragedi',
    r'\btr4gedi\b': 'tragedi',
    r'\btrag3di\b': 'tragedi',
    r'\bt3rs4ngk4\b': 'tersangka',
    r'\bt3rsangka\b': 'tersangka',
    r'\bters4ngk4\b': 'tersangka',
    r'\bt3w4s\b': 'tewas',
    r'\btew4s\b': 'tewas',
    r'\bt3was\b': 'tewas',
    r'\bk0rb4n\b': 'korban',
    r'\bk0rban\b': 'korban',
    r'\bkorb4n\b': 'korban',
    r'\bp3l4ku\b': 'pelaku',
    r'\bp3laku\b': 'pelaku',
    r'\bpel4ku\b': 'pelaku',
    r'\bd1bvnuh\b': 'dibunuh',
    r'\bd1bunuh\b': 'dibunuh',
    r'\bdibvnuh\b': 'dibunuh',
    r'\bm3mbvnuh\b': 'membunuh',
    r'\bm3mbunuh\b': 'membunuh',
    r'\bmembvnuh\b': 'membunuh',
    r'\bp3mbvnuhan\b': 'pembunuhan',
    r'\bp3mbunuhan\b': 'pembunuhan',
    r'\bpembvnuhan\b': 'pembunuhan',
    r'\bbvnuh\b': 'bunuh',
    r'\bbwnuh\b': 'bunuh',
    r'\bmut1l4s1\b': 'mutilasi',
    r'\bmut1lasi\b': 'mutilasi',
    r'\bmutil4si\b': 'mutilasi',
    r'\bd4r4h\b': 'darah',
    r'\bd4rah\b': 'darah',
    r'\br4cun\b': 'racun',
    r'\brac1n\b': 'racun',
    r'\bj4s4d\b': 'jasad',
    r'\bj4sad\b': 'jasad',
    r'\bm4y4t\b': 'mayat',
    r'\bm4yat\b': 'mayat',
    r'\bk3j4h4t4n\b': 'kejahatan',
    r'\bk3jahatan\b': 'kejahatan',
    r'\b0t4psi\b': 'otopsi',
    r'\b4ut0ps1\b': 'autopsi',
    r'\baut0psi\b': 'autopsi',
    r'\bautops1\b': 'autopsi',
    r'\bp0l1s1\b': 'polisi',
    r'\bp0lisi\b': 'polisi',
    r'\bpol1si\b': 'polisi',
}


def clean_algospeak(text: str) -> str:
    """Convert any leetspeak/algospeak censored words back to standard Indonesian for TTS."""
    if not isinstance(text, str):
        return text

    for pattern, replacement in ALGOSPEAK_MAP.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    def _fix_word(match):
        w = match.group(0)
        if re.match(r'^ke-\d+$', w, re.IGNORECASE):
            return w
        if re.search(r'[a-zA-Z]', w) and re.search(r'\d', w):
            sub_map = {'0': 'o', '1': 'i', '3': 'e', '4': 'a', '5': 's', '7': 't', '8': 'b'}
            return ''.join(sub_map.get(ch, ch) for ch in w)
        return w

    text = re.sub(r'\b[a-zA-Z0-9_-]+\b', _fix_word, text)
    return text


def num_to_words_id(n: int) -> str:
    if n == 0:
        return 'nol'
    satuan = ['', 'satu', 'dua', 'tiga', 'empat', 'lima', 'enam', 'tujuh', 'delapan', 'sembilan', 'sepuluh', 'sebelas']
    if n < 12:
        return satuan[n]
    if n < 20:
        return num_to_words_id(n - 10) + ' belas'
    if n < 100:
        return satuan[n // 10] + ' puluh' + ((' ' + num_to_words_id(n % 10)) if n % 10 != 0 else '')
    if n < 200:
        return 'seratus' + ((' ' + num_to_words_id(n - 100)) if n - 100 != 0 else '')
    if n < 1000:
        return satuan[n // 100] + ' ratus' + ((' ' + num_to_words_id(n % 100)) if n % 100 != 0 else '')
    if n < 2000:
        return 'seribu' + ((' ' + num_to_words_id(n - 1000)) if n - 1000 != 0 else '')
    if n < 1000000:
        return num_to_words_id(n // 1000) + ' ribu' + ((' ' + num_to_words_id(n % 1000)) if n % 1000 != 0 else '')
    if n < 1000000000:
        return num_to_words_id(n // 1000000) + ' juta' + ((' ' + num_to_words_id(n % 1000000)) if n % 1000000 != 0 else '')
    if n < 1000000000000:
        return num_to_words_id(n // 1000000000) + ' miliar' + ((' ' + num_to_words_id(n % 1000000000)) if n % 1000000000 != 0 else '')
    return str(n)


def replace_numbers_id(text: str) -> str:
    """Convert all numeric digits to spelled-out Indonesian words for TTS."""
    if not isinstance(text, str):
        return text
    # 1. Ordinals: ke-1, ke-2
    text = re.sub(r'\bke-(\d+)\b', lambda m: ('pertama' if m.group(1) == '1' else ('ke' + num_to_words_id(int(m.group(1))))), text, flags=re.IGNORECASE)
    # 2. Decimal percentages: 99.9% / 99,9%
    text = re.sub(r'(\d+)[.,](\d+)\s*%', lambda m: f"{num_to_words_id(int(m.group(1)))} koma {num_to_words_id(int(m.group(2)))} persen", text)
    # 3. Percentages: 50%
    text = re.sub(r'(\d+)\s*%', lambda m: f"{num_to_words_id(int(m.group(1)))} persen", text)
    # 4. Decimals: 3.5 / 3,5
    text = re.sub(r'(\d+)[.,](\d+)', lambda m: f"{num_to_words_id(int(m.group(1)))} koma {num_to_words_id(int(m.group(2)))}", text)
    # 5. Standalone integers
    text = re.sub(r'\b(\d+)\b', lambda m: num_to_words_id(int(m.group(1))), text)
    return text


import asyncio
import os
import time
from pathlib import Path
import edge_tts
from .config import CONFIG
from elevenlabs.client import ElevenLabs


# ============================================================
# Voice Variety System
# ============================================================

def _get_voice_config() -> dict:
    """Get voice config with variety support."""
    cfg = CONFIG.get("voice", {})
    variety = cfg.get("variety", {})

    if variety.get("enabled", False):
        voices = variety.get("voices", [])
        strategy = variety.get("strategy", "round_robin")

        if voices:
            voice = _select_voice(voices, strategy)
            return {
                **cfg,
                "voice": voice.get("edge_id", cfg.get("voice")),
                "elevenlabs_voice_id": voice.get("elevenlabs_id"),
                "_voice_name": voice.get("name"),
                "_voice_gender": voice.get("gender"),
            }

    return cfg


def _select_voice(voices: list[dict], strategy: str) -> dict:
    """Select voice based on strategy."""
    from . import state

    s = state.load()
    voice_idx = s.get("_voice_idx", 0)

    if strategy == "round_robin":
        selected = voices[voice_idx % len(voices)]
        state.update({"_voice_idx": voice_idx + 1})
    elif strategy == "random":
        import random
        selected = random.choice(voices)
    else:
        selected = voices[voice_idx % len(voices)]
        state.update({"_voice_idx": voice_idx + 1})

    print(f"    voice: selected {selected.get('name', 'unknown')} ({selected.get('gender', '?')})")
    return selected


# ============================================================
# TTS Synthesis
# ============================================================

def _synth_edge(text: str, out_path: Path, v: dict) -> None:
    async def _go():
        com = edge_tts.Communicate(
            text,
            voice=v["voice"],
            rate=v.get("rate", "+0%"),
            pitch=v.get("pitch", "+0Hz"),
        )
        await com.save(str(out_path))
    asyncio.run(_go())


def _synth_elevenlabs(text: str, out_path: Path, v: dict, api_key: str) -> None:
    client = ElevenLabs(api_key=api_key)
    model_id = v.get("elevenlabs_model", "eleven_multilingual_v2")
    audio = client.text_to_speech.convert(
        voice_id=v.get("elevenlabs_voice_id", "21m00Tcm4TlvDq8ikWAM"),
        text=text,
        model_id=model_id,
        output_format="mp3_44100_128",
    )
    with open(out_path, "wb") as f:
        for chunk in audio:
            if chunk:
                f.write(chunk)



def _speed_up(audio_path: Path, rate: float = 1.15):
    import subprocess
    tmp = audio_path.with_suffix(".tmp.mp3")
    subprocess.run(["ffmpeg", "-y", "-i", str(audio_path), "-filter:a", f"atempo={rate}", str(tmp)], capture_output=True)
    tmp.replace(audio_path)


def synth(text: str, out_path: Path) -> Path:
    text = replace_numbers_id(clean_algospeak(text))
    v = _get_voice_config()
    voice_name = v.get("_voice_name", v["voice"])
    print(f"    voice: {voice_name}, {len(text)} chars")

    t0 = time.time()
    provider = CONFIG.get("voice", {}).get("provider", "elevenlabs")

    # ElevenLabs is PRIMARY - try all keys with retry
    if provider == "elevenlabs":
        keys_str = os.environ.get("ELEVENLABS_API_KEYS", "")
        import re
        keys = [k.strip() for k in re.split(r',|\n|\\n', keys_str) if k.strip()]

        if keys:
            for i, api_key in enumerate(keys):
                for attempt in range(2):
                    try:
                        _synth_elevenlabs(text, out_path, v, api_key)
                        print(f"    done in {time.time()-t0:.1f}s (elevenlabs key[{i}], attempt {attempt+1})")
                        return out_path
                    except Exception as e:
                        err_msg = str(e).lower()
                        if "rate" in err_msg or "limit" in err_msg or "429" in err_msg:
                            print(f"    key[{i}] rate limited (attempt {attempt+1}), trying next")
                            break
                        elif "paid_plan_required" in err_msg or "402" in err_msg:
                            print(f"    key[{i}] needs paid plan, trying next")
                            break
                        else:
                            print(f"    key[{i}] error (attempt {attempt+1}): {e}")
                            if attempt == 0:
                                import time as _time
                                _time.sleep(1)
                            continue
            print(f"    all {len(keys)} elevenlabs keys exhausted")
        else:
            print(f"    no elevenlabs keys found")

    # Edge-TTS is LAST RESORT fallback only
    print(f"    falling back to edge-tts (last resort)")
    _synth_edge(text, out_path, v)
    if not out_path.exists() or out_path.stat().st_size < 1024:
        raise RuntimeError(
            f"edge-tts produced invalid audio ({out_path.stat().st_size if out_path.exists() else 0} bytes). "
            "All voice providers failed."
        )
    print(f"    done in {time.time()-t0:.1f}s (edge-tts fallback)")
    return out_path

