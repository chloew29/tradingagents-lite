"""LLM 封裝：OpenAI-compatible，純標準庫（urllib），零依賴。

環境變數：
- AI_API_KEY   有先啟用 LLM（無 key 就行 rule-based，唔會靜靜雞扮有 AI）
- AI_BASE_URL  預設 Groq 免費層；Gemini 例：https://generativelanguage.googleapis.com/v1beta/openai/
- AI_MODEL     無預設 —— 唔估模型名，唔設就唔用 LLM
"""
import json
import os
import urllib.request


def llm_enabled() -> bool:
    return bool(os.environ.get("AI_API_KEY") and os.environ.get("AI_MODEL"))


def llm_name() -> str:
    return os.environ.get("AI_MODEL", "rule-based fallback")


def chat(system: str, user: str, temperature: float = 0.3,
         max_tokens: int = 600) -> str:
    """調一次 chat completion。失敗就拋錯，由上層決定 fallback。"""
    key = os.environ["AI_API_KEY"]
    base = os.environ.get("AI_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.environ["AI_MODEL"]
    req = urllib.request.Request(
        f"{base.rstrip('/')}/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature, "max_tokens": max_tokens,
        }).encode(),
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]
