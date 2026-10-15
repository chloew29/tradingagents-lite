"""技術面分析師：只睇價量，唔估原因。

評分邏輯（啟發式，透明可審計）：
- 趨勢：收盤價 vs MA50/MA200（+1 / -1）
- 動量：RSI(14) > 55 偏多、< 45 偏淡；MACD 線上穿/下穿信號線
- 位置：52 週高低點分位
- 波動：ATR 相對過去一年分位（只作風險提示，唔入分）
"""
import pandas as pd
from agents.base import Analyst, View
from tools.indicators import sma, rsi, atr, macd, max_drawdown


class TechnicalAnalyst(Analyst):
    name = "technical"
    role = "技術面分析師：趨勢、動量、位置，只講圖表講乜"

    def analyze(self, ticker: str, df: pd.DataFrame) -> View:
        close = df["Close"]
        price = float(close.iloc[-1])
        ma50 = float(sma(close, 50).iloc[-1])
        ma200 = float(sma(close, 200).iloc[-1])
        r = float(rsi(close).iloc[-1])
        macd_line, macd_sig = macd(close)
        macd_bull = bool(macd_line.iloc[-1] > macd_sig.iloc[-1])
        hi52, lo52 = float(close.tail(252).max()), float(close.tail(252).min())
        pos52 = (price - lo52) / (hi52 - lo52) if hi52 > lo52 else 0.5
        a = atr(df["High"], df["Low"], close)
        atr_now, atr_med = float(a.iloc[-1]), float(a.tail(252).median())
        mdd, mdd_date = max_drawdown(close)

        score, reasons = 0.0, []
        fmt = lambda x: "n/a（數據唔夠）" if pd.isna(x) else f"{x:.0f}"
        if price > ma50 > ma200:
            score += 1.0; reasons.append(f"多頭排列：現價 {price:.0f} > MA50 {ma50:.0f} > MA200 {ma200:.0f}")
        elif price < ma50 < ma200:
            score -= 1.0; reasons.append(f"空頭排列：現價 {price:.0f} < MA50 {ma50:.0f} < MA200 {ma200:.0f}")
        else:
            reasons.append(f"均線糾纏：現價 {price:.0f}，MA50 {fmt(ma50)}，MA200 {fmt(ma200)}（無趨勢）")
        if r > 55:
            score += 0.5; reasons.append(f"RSI {r:.1f}：動量偏強")
        elif r < 45:
            score -= 0.5; reasons.append(f"RSI {r:.1f}：動量偏弱")
        else:
            reasons.append(f"RSI {r:.1f}：中性")
        score += 0.5 if macd_bull else -0.5
        reasons.append(f"MACD {'金叉偏多' if macd_bull else '死叉偏淡'}")
        if pos52 > 0.8:
            score -= 0.5; reasons.append(f"52 週位置 {pos52:.0%}：接近高位，追高風險")
        elif pos52 < 0.2:
            score += 0.5; reasons.append(f"52 週位置 {pos52:.0%}：接近低位")
        if atr_now > 2 * atr_med:
            reasons.append(f"⚠️ ATR {atr_now:.1f} 係中位數 {atr_med:.1f} 嘅兩倍以上：波動異常")
        reasons.append(f"歷史最大回撤 {mdd:.1%}（{mdd_date.date()}）")

        stance = "bullish" if score > 0.5 else "bearish" if score < -0.5 else "neutral"
        return View(self.name, self.role, stance, score, reasons, {
            "price": round(price, 2), "ma50": round(ma50, 2), "ma200": round(ma200, 2),
            "rsi14": round(r, 1), "macd_bullish": macd_bull,
            "pos_52w": round(pos52, 3), "atr": round(atr_now, 2),
        })
