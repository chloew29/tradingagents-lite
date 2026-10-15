# TradingAgents-lite — A Multi-Agent Investment Debate Framework, Built From Scratch

A simplified re-implementation of the core idea behind [TradingAgents](https://github.com/TauricResearch/TradingAgents):
instead of one LLM making a call from a single prompt, **several role-based agents debate → risk management gets veto power → a trader makes the final call**.
The full transcript is saved, so when something is wrong you can see exactly who was wrong.

```
              ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
              │ Fundamental  │  │  Technical   │  │  Sentiment   │
              │   Analyst    │  │   Analyst    │  │   Analyst    │
              └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                     └────────┬───────┴────────┬────────┘
                              ▼                ▼
                     Round 1 stances → Round 2 rebuttals (debate.py)
                              │
                     ┌────────▼────────┐
                     │  Risk Officer   │── veto power: circuit breaker /
                     │  (doesn't vote) │   position cap / volatility guard
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │  Trader         │── weighted score → BUY/HOLD/SELL
                     └─────────────────┘
                              ▼
              debate_transcript.md ＋ decision.json
```

## Quickstart

```bash
pip install -r requirements.txt
python run_demo.py                      # SPY, latest data
python run_demo.py --ticker AAPL        # needs network (yfinance)
python run_demo.py --asof 2024-06-01    # decide "as of" a past date: a no-look-ahead demo
```

Output: `debate_transcript.md` (human-readable debate log) ＋ `decision.json` (machine-readable).

## Why debate instead of voting?

A single vote averages disagreements away. Debate forces each role to confront the strongest opposing argument —
technical says "bullish alignment", fundamental can rebut "but forward P/E of 24 is expensive".
The transcript stays on record, so post-mortems show which link failed. That is the actual value of multi-agent,
not "three LLMs each saying something once".

## Plugging in an LLM (optional)

It runs fine without a key — the debate falls back to template rebuttals, and the transcript says so explicitly.
With a key you get real LLM debate:

```bash
export AI_API_KEY="..."             # enables LLM only when set
export AI_MODEL="gemini-2.0-flash"  # no default; model names are not guessed
# Gemini via OpenAI-compatible endpoint, for example:
export AI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
python run_demo.py
```

The LLM only **writes rebuttals and the summary** — scores and decision logic are rule-based and never
polluted by hallucination.

## Honest limitations

- A decision-framework demo, **not live-trading advice**. Running ≠ profitable.
- Sentiment defaults to sample headlines (`data/headlines_sample.json`, marked SAMPLE);
  fundamentals fall back to a snapshot when offline (stamped with `as_of`). Wire up NewsAPI /
  live filings for the full version.
- Sentiment has a FinBERT slot (`sentiment.finbert_score`) — install transformers and it upgrades automatically.
- `--asof` is a discipline demo: even the sample headlines are date-filtered, so no future data
  is used to play prophet.

## What this project teaches

1. **Role specialization > one giant prompt**: each agent has limited tools and a narrow view, so the hallucination surface is small.
2. **Debate > voting**: the rebuttal round is the soul of multi-agent.
3. **Independent risk**: it doesn't vote, but it has veto power — same as real funds, where risk is not a subordinate of research.
4. **Auditability**: the transcript is the lab notebook; when wrong, you know who was wrong.

## Next steps

- Real FinBERT (`pip install transformers torch`, set `use_finbert=True`)
- Live news via NewsAPI
- Walk-forward: run the debate monthly and score decision hit-rate (paper trading)
- A second trader: bull/bear dual-trader debate (the original paper's architecture)
