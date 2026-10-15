"""一鍵 demo：對一隻標的跑完整「分析 → 辯論 → 風控 → 決策」。

    python run_demo.py                  # SPY，用最新數據
    python run_demo.py --ticker AAPL    # 要有網（yfinance）
    python run_demo.py --asof 2024-06-01  # 站喺過去某日做決策（無前視偏差演示）

產出：debate_transcript.md（人讀）＋ decision.json（機器讀）
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.market_data import get_daily
from agents.fundamental import FundamentalAnalyst
from agents.technical import TechnicalAnalyst
from agents.sentiment import SentimentAnalyst
from agents.risk import RiskOfficer
from debate import run_debate
from trader import decide
from llm import llm_enabled, llm_name


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", default="SPY")
    ap.add_argument("--asof", default=None, help="YYYY-MM-DD，只用呢日之前嘅數據")
    args = ap.parse_args()

    df, source = get_daily(args.ticker)
    asof = args.asof or str(df.index[-1].date())
    df = df[df.index <= asof]
    print(f"ticker={args.ticker} asof={asof} rows={len(df)} source={source} "
          f"llm={llm_name()}")

    analysts = [FundamentalAnalyst(), TechnicalAnalyst(),
               SentimentAnalyst(asof=args.asof)]
    debate = run_debate(analysts, args.ticker, df)
    risk_view = RiskOfficer().analyze(args.ticker, df)
    decision = decide(debate, risk_view)

    (ROOT / "decision.json").write_text(
        json.dumps({"ticker": args.ticker, "asof": asof,
                    "data_source": source, **decision.to_dict()},
                   ensure_ascii=False, indent=2))
    (ROOT / "debate_transcript.md").write_text(
        render_transcript(args.ticker, asof, source, debate, risk_view, decision))
    print(f"\n決策：{decision.action}（目標倉位 {decision.position_pct:.0%}）")
    print("已寫：debate_transcript.md、decision.json")


def render_transcript(ticker, asof, source, debate, risk_view, decision) -> str:
    L = [f"# TradingAgents-lite 辯論實錄：{ticker}",
         f"- 決策日期：{asof}（只用呢日之前嘅數據）",
         f"- 行情來源：{source}",
         f"- LLM：{llm_name()}（{'有' if debate.llm_used else '無'}啟用）",
         f"- 生成時間：{date.today()}",
         "", "## Round 1：各自立場"]
    for v in debate.views:
        L += [f"### {v.agent}（{v.role}）",
              f"立場：**{v.stance}**（{v.score:+.1f}）", ""]
        L += [f"- {r}" for r in v.reasons] + [""]
    L += ["## Round 2：質詢反駁"]
    for v in debate.views:
        L += [f"### {v.agent} 反駁", debate.rebuttals[v.agent], ""]
    L += ["## 主持人總結", debate.summary, "",
          "## 風控官約束（有否決權）"]
    L += [f"- {r}" for r in risk_view.reasons]
    L += [f"- 硬約束：{'；'.join(risk_view.data['constraints'])}", "",
          "## 最終決策",
          f"- 動作：**{decision.action}**",
          f"- 目標倉位：{decision.position_pct:.0%}",
          f"- 加權總分：{decision.score:+.2f}",
          f"- 理由：{decision.rationale}", "",
          "---",
          "### 誠實聲明",
          "- 決策框架演示，唔係實盤建議；過去表現唔代表未來。",
          "- 情緒面用示例標題、基本面可能係快照 —— 接實時數據源先係完整版。",
          "- 無 LLM key 時辯論係模板反駁；有 key 先係真 LLM 辯論，transcript 會註明。"]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
