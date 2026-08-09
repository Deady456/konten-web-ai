import os
import re
from pathlib import Path
import yaml
from dotenv import load_dotenv

try:
    import truststore
    truststore.inject_into_ssl()
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

with open(ROOT / "config.yaml", "r", encoding="utf-8") as f:
    CONFIG = yaml.safe_load(f)

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
STATE_FILE = ROOT / "state.json"

_pexels_keys = []
for k, v in os.environ.items():
    if k.startswith("PEXELS_API_KEY") and v.strip():
        import re
        _pexels_keys.extend([x.strip().strip('\"').strip('\'') for x in re.split(r',|\n|\\n', v) if x.strip()])
PEXELS_API_KEYS = _pexels_keys if _pexels_keys else ["dummy_key"]
_nvkeys = []
for k, v in os.environ.items():
    if k.startswith("NVIDIA_API_KEY") and v.strip():
        _nvkeys.extend([x.strip().strip('"').strip("'") for x in re.split(r',|\n|\\n', v) if x.strip()])
NVIDIA_API_KEYS = _nvkeys if _nvkeys else ["dummy"]

import random
random.shuffle(PEXELS_API_KEYS)
_cfg_model = CONFIG.get("script", {}).get("model", "")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "nvidia" if ("nvidia" in _cfg_model.lower() or "meta/" in _cfg_model.lower() or "llama" in _cfg_model.lower() or "nemotron" in _cfg_model.lower() or "step" in _cfg_model.lower()) else ("gemini" if "gemini" in _cfg_model.lower() else "groq"))
_gkeys = []
for k, v in os.environ.items():
    if k.startswith("GEMINI_API_KEY") and v.strip():
        _gkeys.extend([x.strip().strip('\"').strip('\'') for x in re.split(r',|\n|\\n', v) if x.strip()])
GEMINI_API_KEYS = _gkeys if _gkeys else [""]
GEMINI_API_KEY = GEMINI_API_KEYS[0]

_grkeys = []
for k, v in os.environ.items():
    if k.startswith("GROQ_API_KEY") and v.strip():
        _grkeys.extend([x.strip().strip('\"').strip('\'') for x in re.split(r',|\n|\\n', v) if x.strip()])
GROQ_API_KEYS = _grkeys if _grkeys else ["dummy"]

if LLM_PROVIDER == "gemini":
    LLM_API_KEY = GEMINI_API_KEY
    LLM_API_KEYS = GEMINI_API_KEYS
    LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
    LLM_MODEL = CONFIG.get("script", {}).get("model", "models/gemini-2.5-flash")
elif LLM_PROVIDER == "nvidia":
    LLM_API_KEYS = NVIDIA_API_KEYS
    LLM_API_KEY = LLM_API_KEYS[0]
    LLM_BASE_URL = "https://integrate.api.nvidia.com/v1"
    LLM_MODEL = CONFIG.get("script", {}).get("model", "meta/llama-3.3-70b-instruct")
elif LLM_PROVIDER == "openrouter":
    _orkeys = []
    for k, v in os.environ.items():
        if k.startswith("OPENROUTER_API_KEY") and v.strip():
            _orkeys.extend([x.strip().strip('"').strip("'") for x in re.split(r',|\n|\\n', v) if x.strip()])
    OPENROUTER_API_KEYS = _orkeys if _orkeys else [""]
    LLM_API_KEYS = OPENROUTER_API_KEYS
    LLM_API_KEY = LLM_API_KEYS[0]
    LLM_BASE_URL = "https://openrouter.ai/api/v1"
    LLM_MODEL = CONFIG.get("script", {}).get("model", "meta-llama/llama-3.3-70b-instruct")
elif LLM_PROVIDER == "groq":
    LLM_API_KEYS = GROQ_API_KEYS
    LLM_API_KEY = LLM_API_KEYS[0]
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
    LLM_MODEL = CONFIG.get("script", {}).get("model", "llama-3.3-70b-versatile")
elif LLM_PROVIDER == "omniroute":
    _model = CONFIG.get("script", {}).get("model", "")
    if "llama" in _model.lower() or "mixtral" in _model.lower() or "gemma" in _model.lower():
        LLM_API_KEYS = GROQ_API_KEYS
    else:
        LLM_API_KEYS = GEMINI_API_KEYS
    LLM_API_KEY = LLM_API_KEYS[0] if LLM_API_KEYS else "dummy"
    LLM_BASE_URL = "https://vocalize-turmoil-gizmo.ngrok-free.dev/v1"
    LLM_MODEL = CONFIG.get("script", {}).get("model", "gemini-2.5-flash")
else:
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER}")
