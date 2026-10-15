"""基本面分析師：估值＋盈利，睇貴唔貴、賺唔賺到錢。

數據：yfinance 優先；失敗就用 data/fundamentals_snapshot.json
（快照會標明 as_of 同 stale，唔會扮係實時）。
評分係粗糙啟發式 —— 作用係「有個識睇財報嘅人喺枱面」，唔係精準估值。
"""
import json
import pandas as pd
from pathlib import Path
from agents.base import Analyst, View

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SNAPSHOT = DATA_DIR / "fundamentals_snapshot.json"


def get_fundamentals(ticker: str) -> tuple[dict, str]:
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info or {}
        f = {
            "trailing_pe": info.get("trailingPE"),
            "forward_pe": info.get("forwardPE"),
            "price_to_book": info.get("priceToBook"),
            "profit_margin": info.get("profitMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "market_cap": info.get("marketCap"),
        }
        if f["trailing_pe"] is None and f["forward_pe"] is None:
            raise ValueError("no valuation fields")
        f.update({"as_of": "yfinance realtime", "stale": False})
        return f, "yfinance"
    except Exception as e:
        print(f"[fundamental] yfinance 失敗 ({e})，用快照")
    snap = json.loads(SNAPSHOT.read_text())
    f = dict(snap.get(ticker, snap.get("SPY")))
    f["stale"] = True
    return f, f"snapshot as_of {f.get('as_of')}"


class FundamentalAnalyst(Analyst):
    name = "fundamental"
    role = "基本面分析師：估值貴唔貴、盈利掂唔掂"

    def analyze(self, ticker: str, df: pd.DataFrame) -> View:
        f, source = get_fundamentals(ticker)
        score, reasons = 0.0, [f"數據來源：{source}"]
        pe = f.get("forward_pe") or f.get("trailing_pe")
        if pe:
            if pe < 18:
                score += 1.0; reasons.append(f"Forward P/E {pe:.1f}：估值合理偏平")
            elif pe < 25:
                score += 0.25; reasons.append(f"Forward P/E {pe:.1f}：估值中性偏貴")
            else:
                score -= 1.0; reasons.append(f"Forward P/E {pe:.1f}：估值貴（歷史高位區）")
        pm = f.get("profit_margin")
        if pm is not None:
            if pm > 0.15:
                score += 0.75; reasons.append(f"淨利率 {pm:.1%}：盈利能力強")
            elif pm > 0:
                score += 0.25; reasons.append(f"淨利率 {pm:.1%}：有盈利")
            else:
                score -= 0.75; reasons.append("蝕緊錢：基本面扣分")
        rg = f.get("revenue_growth")
        if rg is not None:
            if rg > 0.1:
                score += 0.5; reasons.append(f"營收增長 {rg:.1%}：成長強勁")
            elif rg < 0:
                score -= 0.5; reasons.append(f"營收增長 {rg:.1%}：萎縮中")
        if f.get("stale"):
            reasons.append("⚠️ 基本面係快照數據，唔係實時，結論要打折")
        stance = "bullish" if score > 0.5 else "bearish" if score < -0.5 else "neutral"
        return View(self.name, self.role, stance, score, reasons, {k: v for k, v in f.items()})
