"""Debate moderator: two rounds.

Round 1: three analysts submit views (fundamental / technical / sentiment).
Round 2: each analyst rebuts the one with the most opposing stance.
Risk officer does not debate; its constraints go straight to the trader.
"""
from dataclasses import dataclass
from agents.base import View
import llm


@dataclass
class DebateResult:
    views: list      # list[View]
    rebuttals: dict  # agent -> rebuttal text
    summary: str
    llm_used: bool


def _template_rebuttal(me: View, opp: View) -> str:
    mine = "; ".join(me.reasons[:2])
    theirs = "; ".join(opp.reasons[:2])
    return (
        "維持" + me.stance + "（" + format(me.score, "+.1f") + "）：" + mine + "。"
        "對方" + opp.agent + "睇" + opp.stance + "（" + format(opp.score, "+.1f") + "）："
        + theirs + "。分歧核心係時間框架同數據維度唔同，我嘅結論唔變，"
        "但承認對方論據成立時我嘅分數要打折。"
    )


def _llm_rebuttal(me: View, opp: View) -> str:
    system = (
        "你係一位嚴謹嘅投資分析師，正喺投資委員會辯論。"
        "用繁體中文，150 字內，直指對方論據最弱一環，唔好講廢話。"
    )
    user = (
        "你嘅角色：" + me.role + "\n"
        "你嘅立場：" + me.stance + "（" + format(me.score, "+.1f") + "分）\n"
        "你嘅理由：" + "; ".join(me.reasons) + "\n\n"
        "反方（" + opp.agent + "，" + opp.role + "）立場：" + opp.stance
        + "（" + format(opp.score, "+.1f") + "分）\n"
        "反方理由：" + "; ".join(opp.reasons) + "\n\n請寫你嘅反駁。"
    )
    return llm.chat(system, user).strip()


def _llm_summary(views: list, rebuttals: dict) -> str:
    system = (
        "你係投資委員會主席。用繁體中文，200 字內總結三方辯論："
        "最大共識、最大分歧、邊個論據最硬。唔好落投資結論，只總結辯論。"
    )
    parts = []
    for v in views:
        parts.append(
            "【" + v.agent + "】" + v.stance + "（" + format(v.score, "+.1f") + "）："
            + "; ".join(v.reasons) + "\n反駁：" + rebuttals[v.agent]
        )
    return llm.chat(system, "\n\n".join(parts)).strip()


def _template_summary(views: list, rebuttals: dict) -> str:
    scores = {v.agent: round(v.score, 2) for v in views}
    bull = [v.agent for v in views if v.stance == "bullish"]
    bear = [v.agent for v in views if v.stance == "bearish"]
    return (
        "三方分數：" + str(scores) + "。睇好：" + str(bull or "無")
        + "；睇淡：" + str(bear or "無") + "。"
        "最大分歧喺時間框架：技術面睇趨勢動量，基本面睇估值，情緒面睇短期預期。"
        "（模板總結 —— 設 AI_API_KEY+AI_MODEL 啟用 LLM 主持）"
    )


def _pick_opponent(me: View, views: list) -> View:
    others = [v for v in views if v is not me]
    opps = [v for v in others if v.score * me.score < 0]
    pool = opps if opps else others
    return max(pool, key=lambda v: abs(v.score - me.score))


def run_debate(analysts, ticker: str, df) -> DebateResult:
    views = [a.analyze(ticker, df) for a in analysts]
    use_llm = llm.llm_enabled()
    rebuttals = {}
    for me in views:
        opp = _pick_opponent(me, views)
        if use_llm:
            try:
                rebuttals[me.agent] = _llm_rebuttal(me, opp)
            except Exception as e:
                print("[debate] LLM rebuttal failed (" + str(e) + "), using template")
                rebuttals[me.agent] = _template_rebuttal(me, opp)
                use_llm = False
        else:
            rebuttals[me.agent] = _template_rebuttal(me, opp)
    if use_llm:
        try:
            summary = _llm_summary(views, rebuttals)
        except Exception as e:
            print("[debate] LLM summary failed (" + str(e) + "), using template")
            summary = _template_summary(views, rebuttals)
            use_llm = False
    else:
        summary = _template_summary(views, rebuttals)
    return DebateResult(views, rebuttals, summary, use_llm)
