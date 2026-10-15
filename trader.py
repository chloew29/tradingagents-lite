"""交易員：汇总辯論 → 落最終決定。

流程：
1. 加權分數：technical 0.35 / fundamental 0.35 / sentiment 0.30
   （技術同基本面係慢變量，權重高；情緒係快變量，權重低 —— 寫死喺度，透明）
2. 風控約束：veto → 強制 HOLD/減倉；否則倉位唔超過風控上限
3. 決策：score > 0.7 買入，< -0.7 賣出（long-only 即減倉至 0），之間 HOLD
4. rationale：有 LLM 就 LLM 寫，否則模板

注意：呢個係「決策框架演示」，唔係實盤建議。
"""
from dataclasses import dataclass
from debate import DebateResult
from agents.base import View
import llm

WEIGHTS = {"technical": 0.35, "fundamental": 0.35, "sentiment": 0.30}


@dataclass
class Decision:
    action: str            # BUY / HOLD / SELL
    position_pct: float    # 目標倉位（0~1）
    score: float           # 加權總分
    rationale: str
    llm_used: bool

    def to_dict(self):
        return {"action": self.action,
                "position_pct": round(self.position_pct, 3),
                "score": round(self.score, 3),
                "rationale": self.rationale,
                "llm_used": self.llm_used}


def _template_rationale(debate, risk_view, score, action, position, cap):
    lines = [f"加權總分 {score:+.2f}（技術x0.35＋基本面x0.35＋情緒x0.30）"]
    for v in debate.views:
        lines.append(f"－{v.agent}：{v.stance}（{v.score:+.1f}）：{v.reasons[0]}")
    lines.append(f"風控：{'；'.join(risk_view.data.get('constraints', []))}，倉位上限 {cap:.0%}")
    lines.append(f"決定：{action}，目標倉位 {position:.0%}")
    return "\n".join(lines)


def decide(debate: DebateResult, risk_view: View) -> Decision:
    score = sum(v.score * WEIGHTS[v.agent] for v in debate.views)
    veto = bool(risk_view.data.get("veto"))
    cap = float(risk_view.data.get("max_position_pct", 1.0))

    if veto:
        action, position = "HOLD", 0.0
        why_veto = "; ".join(risk_view.data.get("constraints", []))
        rationale = f"風控否決：{why_veto}。辯論總分 {score:+.2f} 作廢，保命先。"
        return Decision(action, position, score, rationale, False)

    if score > 0.7:
        action, position = "BUY", min(cap, 0.5 + score / 4)
    elif score < -0.7:
        action, position = "SELL", 0.0
    else:
        action, position = "HOLD", min(cap, 0.25)

    used = False
    if llm.llm_enabled():
        try:
            rationale = llm.chat(
                "你係交易員。用繁體中文，150 字內解釋點解落呢個決定，"
                "要引用各分析師分數同風控約束。",
                f"加權總分 {score:+.2f}（權重 {WEIGHTS}）；"
                + "; ".join(f"{v.agent} {v.stance}({v.score:+.1f})"
                            for v in debate.views)
                + f"；風控：倉位上限 {cap:.0%}，"
                + f"{'; '.join(risk_view.data.get('constraints', []))}；"
                f"決定：{action}，目標倉位 {position:.0%}。").strip()
            used = True
        except Exception as e:
            print(f"[trader] LLM 失敗 ({e})，轉模板")
            rationale = _template_rationale(debate, risk_view, score,
                                            action, position, cap)
    else:
        rationale = _template_rationale(debate, risk_view, score,
                                        action, position, cap)
    return Decision(action, round(position, 3), score, rationale, used)
