"""行情數據：yfinance 優先，本地快取兜底，全離線都跑得。

設計原則：demo 唔可以因為斷網/限流就跑唔起。
"""
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df[["Open", "High", "Low", "Close", "Volume"]].dropna()


def get_daily(ticker: str, period: str = "2y") -> tuple[pd.DataFrame, str]:
    """回傳 (df, source)。source 係 'yfinance' / 'cache' / 'fallback'。

    優先順序：yfinance 下載 → 寫快取；失敗 → 讀快取；再失敗 → 內置 fallback。
    """
    cache = DATA_DIR / f"cache_{ticker}_{period}.csv"
    try:
        import yfinance as yf
        df = _normalize(yf.download(ticker, period=period, interval="1d",
                                    auto_adjust=True, progress=False))
        if len(df) < 60:
            raise ValueError("downloaded too few rows")
        df.to_csv(cache)
        return df, "yfinance"
    except Exception as e:
        print(f"[market_data] yfinance 失敗 ({e})，試快取…")
    if cache.exists():
        return pd.read_csv(cache, index_col=0, parse_dates=True), "cache"
    fb = DATA_DIR / f"{ticker.lower()}_fallback.csv"
    if fb.exists():
        print(f"[market_data] 用內置 fallback 數據（{fb.name}）")
        return pd.read_csv(fb, index_col=0, parse_dates=True), "fallback"
    raise RuntimeError(f"無數據可用：{ticker}（yfinance 失敗、無快取、無 fallback）")
