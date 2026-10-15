# TradingAgents-lite — 從零起嘅多智能體投資辯論框架

簡化復刻 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 嘅核心思想：
唔係一個 LLM 一句 prompt 落決定，而係**幾個角色化 Agent 辯論 → 風控否決 → 交易員拍板**，
全程留 transcript，邊個錯一目了然。

```
              ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
              │ Fundamental  │  │  Technical   │  │  Sentiment   │
              │ 基本面分析師 │  │  技術面分析師 │  │  情緒面分析師 │
              └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                     └────────┬───────┴────────┬────────┘
                              ▼                ▼
                     Round 1 立場 → Round 2 質詢反駁（debate.py）
                              │
                     ┌────────▼────────┐
                     │  Risk Officer   │── 否決權：熔斷/倉位上限/波動異常
                     │  風控官（唔投票）│
                     └────────┬────────┘
                              ▼
                     ┌─────────────────┐
                     │  Trader 交易員   │── 加權分數 → BUY/HOLD/SELL
                     └─────────────────┘
                              ▼
              debate_transcript.md ＋ decision.json
```

## 點跑

```bash
pip install -r requirements.txt
python run_demo.py                      # SPY，用最新數據
python run_demo.py --ticker AAPL        # 要有網（yfinance）
python run_demo.py --asof 2024-06-01    # 站喺過去某日做決策，演示無前視偏差
```

產出：`debate_transcript.md`（人讀嘅辯論實錄）＋ `decision.json`（機器讀）。

## 點解要辯論，而唔係投票？

單次投票會將分歧平均掉。辯論迫每個角色直面反方最強論據 ——
技術面話「多頭排列」，基本面可以反駁「但 Forward P/E 24 倍貴」。
transcript 留低，事後覆盤知邊個環節錯。呢個先係 multi-agent 嘅價值，
唔係「三個 LLM 各講一次」。

## 接 LLM（可選）

無 key 照跑 —— 辯論用模板反駁，transcript 會註明。有 key 先係真 LLM 辯論：

```bash
export AI_API_KEY="..."        # 有先啟用
export AI_MODEL="gemini-2.0-flash"   # 無預設，唔估模型名
# Gemini OpenAI-compatible 例：
export AI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai/"
python run_demo.py
```

LLM 只負責**寫反駁文字同總結**，分數同決策邏輯唔經 LLM ——
分數係規則算出嚟嘅，唔會被幻覺污染。

## 誠實聲明

- 決策框架演示，**唔係實盤建議**。跑得唔代表賺得。
- 情緒面預設係示例標題（`data/headlines_sample.json` 有標 SAMPLE），
  基本面離線時用快照（會註明 as_of）。接 NewsAPI / 實時財報先係完整版。
- 情緒面有 FinBERT 插槽（`sentiment.finbert_score`），裝咗 transformers 自動升級。
- `--asof` 係個紀律演示：連示例新聞都會按日期過濾，唔用未來數據扮先知。

## 學到乜（呢個 project 嘅教學點）

1. **角色分工 > 大一統 prompt**：每個 agent 得有限工具同視角，幻覺面細。
2. **辯論 > 投票**：反駁環節先係 multi-agent 嘅靈魂。
3. **風控獨立**：唔投票但有否決權 —— 現實基金都係咁，risk 唔係 research 嘅下屬。
4. **可審計**：transcript 就係實驗記錄，錯咗知邊個錯。

## 下一步

- FinBERT 實裝（`pip install transformers torch`，改 `use_finbert=True`）
- NewsAPI 接實時新聞流
- walk-forward：每個月跑一次辯論，計決策命中率（紙上交易）
- 第二個交易員：bull/bear 雙交易員辯論（原論文架構）
