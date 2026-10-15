"""技術指標：全部只用過去數據，無前視偏差。"""
import pandas as pd
import numpy as np


def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n).mean()


def rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI（同 project1 策略庫一致）。"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()


def macd(close: pd.Series, fast: int = 12, slow: int = 26,
         signal: int = 9) -> tuple[pd.Series, pd.Series]:
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    return line, line.ewm(span=signal, adjust=False).mean()


def max_drawdown(close: pd.Series) -> tuple[float, pd.Timestamp | None]:
    """回傳 (最大回撤, 發生日)。"""
    dd = close / close.cummax() - 1
    return float(dd.min()), dd.idxmin()
