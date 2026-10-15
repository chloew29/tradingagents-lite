"""情緒面分析師：新聞標題情緒，睇市場驚定貪。

v1 用詞典基線（透明、零依賴、離線跑得）；
finbert_score() 係 FinBERT 插槽 —— 裝咗 transformers 就自動升級，
接口唔變。誠實標明而家用緊邊個。
"""
import json
import re
import pandas as pd
from pathlib import Path
from agents.base import Analyst, View

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

POS = {"rally", "surge", "record", "beat", "beats", "upgrade", "upgrades",
       "bullish", "optimism", "optimistic", "growth", "strong", "gains",
       "soar", "soars", "jump", "rebound", "easing", "cut", "cuts",
       "dovish", "stimulus", "breakthrough"}
NEG = {"plunge", "crash", "crashes", "fear", "fears", "recession", "downgrade",
       "downgrades", "miss", "misses", "bearish", "pessimism", "selloff",
       "sell-off", "tumble", "tumbles", "slump", "warning", "warns",
       "hawkish", "hike", "hikes", "tariff", "tariffs", "layoff", "layoffs",
       "default", "crisis", "volatile", "volatility", "uncertainty"}


def lexicon_score(text: str) -> float:
    words = set(re.findall(r"[a-z-]+", text.lower()))
    p = len(words & POS)
    n = len(words & NEG)
    if p == n == 0:
        return 0.0
    return (p - n) / (p + n)


def finbert_score(texts: list[str]) -> list[float]:
    """FinBERT 插槽：有 transformers 先用到，否則拋錯講清楚點裝。"""
    try:
        from transformers import pipeline
    except ImportError:
        raise RuntimeError("未裝 transformers：pip install transformers torch，用詞典基線頂住先")
    clf = pipeline("sentiment-analysis",
                   model="ProsusAI/finbert", truncation=True)
    out = clf(texts)
    mapping = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
    return [mapping[o["label"]] * o["score"] for o in out]


class SentimentAnalyst(Analyst):
    name = "sentiment"
    role = "情緒面分析師：新聞情緒，睇市場驚定貪"

    def __init__(self, headlines_path: Path | None = None,
                 use_finbert: bool = False, asof: str | None = None):
        self.headlines_path = headlines_path or DATA_DIR / "headlines_sample.json"
        self.use_finbert = use_finbert
        self.asof = asof

    def analyze(self, ticker: str, df: pd.DataFrame) -> View:
        items = json.loads(self.headlines_path.read_text())
        if self.asof:
            # 只用決策日之前嘅新聞 —— 唔可以用未來新聞扮先知
            items = [h for h in items if h.get("date", "") <= self.asof]
        if not items:
            return View(self.name, self.role, "neutral", 0.0,
                        [f"{self.asof} 之前無新聞標題，情緒面棄權（唔呃分）"], {"n": 0})
        texts = [h["title"] for h in items]
        try:
            scores = finbert_score(texts) if self.use_finbert else None
            method = "FinBERT (ProsusAI/finbert)"
        except RuntimeError as e:
            print(f"[sentiment] {e}")
            scores, method = None, "lexicon（FinBERT 未裝）"
        if scores is None:
            scores = [lexicon_score(t) for t in texts]
            method = "lexicon baseline"
        avg = sum(scores) / len(scores)
        pos_n = sum(1 for s in scores if s > 0.1)
        neg_n = sum(1 for s in scores if s < -0.1)
        reasons = [
            f"方法：{method}，{len(texts)} 條標題",
            f"偏多 {pos_n} 條 / 偏淡 {neg_n} 條，中性 {len(texts)-pos_n-neg_n} 條",
            f"平均情緒分 {avg:+.2f}（-1~+1）",
        ]
        if self.headlines_path.name == "headlines_sample.json":
            reasons.append("⚠️ 係示例標題唔係實時新聞流 —— 接 NewsAPI 即變實時")
        score = max(-2.0, min(2.0, avg * 2))
        stance = "bullish" if score > 0.5 else "bearish" if score < -0.5 else "neutral"
        return View(self.name, self.role, stance, score, reasons,
                    {"avg_sentiment": round(avg, 3), "n": len(texts),
                     "method": method})
