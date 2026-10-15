"""風控官：唔投票，但有否決權。

職責：
1. 倉位上限：按 ATR 算，單筆風險唔超過淨值 1%（半 Kelly 精神：寧細莫大）
2. 熔斷：現時回撤超過 -15% → 強制 HOLD/減倉，唔畀加倉
3. 波動異常：ATR 係中位數 3 倍以上 → 倉位減半

輸出唔係觀點，係硬約束，trader 必須執行。
"""
import pandas as pd
from agents.base import Analyst, View
from tools.indicators import atr, max_drawdown


class RiskOfficer(Analyst):
    name = "risk"
    role = "風控官：唔睇方向，只睇會唔會死，有否決權"

    def __init__(self, risk_per_trade: float = 0.01, max_drawdown_cut: float = 0.15):
        self.risk_per_trade = risk_per_trade
        self.max_drawdown_cut = max_drawdown_cut

    def analyze(self, ticker: str, df: pd.DataFrame) -> View:
        close = df["Close"]
        price = float(close.iloc[-1])
        a = atr(df["High"], df["Low"], close)
        atr_now, atr_med = float(a.iloc[-1]), float(a.tail(252).median())
        mdd, _ = max_drawdown(close)
        cur_dd = float(close.iloc[-1] / close.cummax().iloc[-1] - 1)

        # 止損距離 = 2×ATR；倉位 = 風險預算 / 止損距離
        stop_pct = 2 * atr_now / price
        size_pct = min(self.risk_per_trade / stop_pct, 1.0)

        constraints, veto = [], False
        reasons = [
            f"ATR {atr_now:.1f}（中位數 {atr_med:.1f}），2×ATR 止損 ≈ {stop_pct:.1%}",
            f"按單筆風險 {self.risk_per_trade:.0%} 計，建議倉位上限 {size_pct:.0%}",
            f"現時回撤 {cur_dd:.1%}（熔斷線 -{self.max_drawdown_cut:.0%}）",
        ]
        if cur_dd < -self.max_drawdown_cut:
            veto = True
            constraints.append("熔斷：回撤超標，唔畀開新倉，只准 HOLD/減倉")
            reasons.append("🚨 熔斷觸發：保命先，方向啱都唔加倉")
        if atr_now > 3 * atr_med:
            size_pct *= 0.5
            constraints.append("波動異常：倉位減半")
            reasons.append("⚠️ 波動異常（ATR > 3×中位數），倉位減半")
        if not constraints:
            constraints.append("無觸發硬約束，按建議倉位上限執行")

        # 風控官嘅 score 唔係方向，係「容許幾大膽」：0 中性，-2 熔斷
        return View(self.name, self.role, "neutral", -2.0 if veto else 0.0, reasons, {
            "veto": veto, "max_position_pct": round(size_pct, 3),
            "stop_pct": round(stop_pct, 4), "current_dd": round(cur_dd, 4),
            "constraints": constraints,
        })
