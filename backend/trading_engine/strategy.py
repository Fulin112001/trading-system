from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from backend.config import get_trading_config

class SignalResult:
    def __init__(self, symbol, direction, confidence, reason, strategy, price, market_state):
        self.symbol = symbol
        self.direction = direction
        self.confidence = confidence
        self.reason = reason
        self.strategy = strategy
        self.price = price
        self.market_state = market_state
        self.created_at = datetime.now()

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "confidence": self.confidence,
            "reason": self.reason,
            "strategy": self.strategy,
            "price": self.price,
            "market_state": self.market_state,
            "created_at": self.created_at.isoformat()
        }

class MACrossoverStrategy:
    def __init__(self):
        config = get_trading_config()["strategies"]["ma_crossover"]
        self.enabled = config["enabled"]
        self.fast_ma = config["fast_ma"]
        self.slow_ma = config["slow_ma"]
        self.long_ma = config["long_ma"]

    def analyze(self, symbol, prices, current_price):
        if not self.enabled:
            return None
        if len(prices) < self.long_ma:
            return None

        fast = sum(prices[-self.fast_ma:]) / self.fast_ma
        slow = sum(prices[-self.slow_ma:]) / self.slow_ma
        long = sum(prices[-self.long_ma:]) / self.long_ma

        prev_fast = sum(prices[-self.fast_ma-1:-1]) / self.fast_ma
        prev_slow = sum(prices[-self.slow_ma-1:-1]) / self.slow_ma

        if prev_fast < prev_slow and fast > slow and current_price > long:
            return SignalResult(
                symbol=symbol,
                direction="BUY",
                confidence=75,
                reason=f"MA{self.fast_ma} 上穿 MA{self.slow_ma}，站上 MA{self.long_ma}",
                strategy="MA_CROSSOVER",
                price=current_price,
                market_state="趨勢市"
            )
        elif prev_fast > prev_slow and fast < slow and current_price < long:
            return SignalResult(
                symbol=symbol,
                direction="SELL",
                confidence=75,
                reason=f"MA{self.fast_ma} 下穿 MA{self.slow_ma}，跌破 MA{self.long_ma}",
                strategy="MA_CROSSOVER",
                price=current_price,
                market_state="趨勢市"
            )
        return SignalResult(
            symbol=symbol,
            direction="HOLD",
            confidence=50,
            reason="無明確交叉訊號",
            strategy="MA_CROSSOVER",
            price=current_price,
            market_state="觀望"
        )

class RSIStrategy:
    def __init__(self):
        config = get_trading_config()["strategies"]["rsi"]
        self.enabled = config["enabled"]
        self.period = config["period"]
        self.overbought = config["overbought"]
        self.oversold = config["oversold"]

    def calculate_rsi(self, prices):
        if len(prices) < self.period + 1:
            return None
        gains, losses = [], []
        for i in range(1, self.period + 1):
            diff = prices[-i] - prices[-i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def analyze(self, symbol, prices, current_price):
        if not self.enabled:
            return None
        rsi = self.calculate_rsi(prices)
        if rsi is None:
            return None

        if rsi < self.oversold:
            return SignalResult(
                symbol=symbol,
                direction="BUY",
                confidence=70,
                reason=f"RSI {rsi:.1f} 低於超賣區 {self.oversold}",
                strategy="RSI",
                price=current_price,
                market_state="超賣反彈"
            )
        elif rsi > self.overbought:
            return SignalResult(
                symbol=symbol,
                direction="SELL",
                confidence=70,
                reason=f"RSI {rsi:.1f} 高於超買區 {self.overbought}",
                strategy="RSI",
                price=current_price,
                market_state="超買回落"
            )
        return SignalResult(
            symbol=symbol,
            direction="HOLD",
            confidence=50,
            reason=f"RSI {rsi:.1f} 在中性區間",
            strategy="RSI",
            price=current_price,
            market_state="中性"
        )

class SignalAggregator:
    def __init__(self):
        self.strategies = [
            MACrossoverStrategy(),
            RSIStrategy(),
        ]
        self.config = get_trading_config()["signal"]

    def analyze(self, symbol, prices, current_price):
        results = []
        for strategy in self.strategies:
            result = strategy.analyze(symbol, prices, current_price)
            if result:
                results.append(result)

        buy_count = sum(1 for r in results if r.direction == "BUY")
        sell_count = sum(1 for r in results if r.direction == "SELL")
        min_confirm = self.config["min_confirm"]

        if buy_count >= min_confirm:
            avg_confidence = sum(r.confidence for r in results if r.direction == "BUY") / buy_count
            reasons = " + ".join(r.reason for r in results if r.direction == "BUY")
            return SignalResult(symbol, "BUY", avg_confidence, reasons, "AGGREGATED", current_price, "多頭確認")
        elif sell_count >= min_confirm:
            avg_confidence = sum(r.confidence for r in results if r.direction == "SELL") / sell_count
            reasons = " + ".join(r.reason for r in results if r.direction == "SELL")
            return SignalResult(symbol, "SELL", avg_confidence, reasons, "AGGREGATED", current_price, "空頭確認")

        return SignalResult(symbol, "HOLD", 50, "訊號未達確認門檻", "AGGREGATED", current_price, "觀望")

if __name__ == "__main__":
    import random
    prices = [100 + random.uniform(-5, 5) for _ in range(80)]
    prices += [p + 2 for p in prices[-10:]]
    current_price = prices[-1]

    aggregator = SignalAggregator()
    signal = aggregator.analyze("2330", prices, current_price)
    print(f"標的：{signal.symbol}")
    print(f"方向：{signal.direction}")
    print(f"信心：{signal.confidence:.1f}%")
    print(f"原因：{signal.reason}")
    print(f"市場：{signal.market_state}")
