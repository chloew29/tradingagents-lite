"""Agent 基類：每個分析師輸出一個結構化觀點（stance + score + 理由 + 數據）。"""
from dataclasses import dataclass
from abc import ABC, abstractmethod
import pandas as pd


@dataclass
class View:
    agent: str                    # 分析師名
    role: str = ""                # 分析師職責（一句話）
    stance: str = "neutral"       # bullish / bearish / neutral
    score: float = 0.0            # -2（極睇淡）~ +2（極睇好）
    reasons: list = None
    data: dict = None

    def __post_init__(self):
        self.score = max(-2.0, min(2.0, float(self.score)))
        if self.reasons is None:
            self.reasons = []
        if self.data is None:
            self.data = {}
        if self.stance not in ("bullish", "bearish", "neutral"):
            raise ValueError(f"bad stance: {self.stance}")


class Analyst(ABC):
    name: str = "analyst"
    role: str = ""

    @abstractmethod
    def analyze(self, ticker: str, df: pd.DataFrame) -> View:
        """df 係截至 asof 嘅日線（含 Open/High/Low/Close/Volume）。"""
