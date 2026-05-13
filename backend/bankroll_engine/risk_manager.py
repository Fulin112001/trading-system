import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))
from backend.config import get_risk_config
from datetime import datetime

class RiskMode:
    NORMAL = "NORMAL"
    DEFENSIVE = "DEFENSIVE"
    LOCKDOWN = "LOCKDOWN"

class RiskManager:
    def __init__(self, capital):
        self.config = get_risk_config()
        self.capital = capital
        self.initial_capital = capital
        self.daily_pnl = 0
        self.consecutive_losses = 0
        self.total_drawdown = 0
        self.mode = RiskMode.NORMAL
        self.trades_today = []
        self.emergency_stop = False

    def check_can_trade(self):
        if self.emergency_stop:
            return False, "緊急停止已啟動"
        if self.mode == RiskMode.LOCKDOWN:
            return False, "風控模式：LOCKDOWN，停止交易"
        daily_loss_limit = self.capital * (self.config["daily_loss_limit_pct"] / 100)
        if self.daily_pnl <= -daily_loss_limit:
            return False, f"已達每日虧損上限 {self.config['daily_loss_limit_pct']}%"
        return True, "允許交易"

    def calculate_position_size(self, price, confidence=50):
        method = self.config["position_size_method"]
        base_pct = self.config["position_size_pct"] / 100

        if self.mode == RiskMode.DEFENSIVE:
            base_pct *= 0.5

        confidence_multiplier = confidence / 100
        final_pct = base_pct * confidence_multiplier
        position_value = self.capital * final_pct
        quantity = position_value / price

        return round(quantity, 4), round(position_value, 2)

    def update_after_trade(self, pnl):
        self.daily_pnl += pnl
        self.capital += pnl
        drawdown = (self.initial_capital - self.capital) / self.initial_capital * 100
        self.total_drawdown = max(self.total_drawdown, drawdown)

        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self._update_mode()

    def _update_mode(self):
        prev_mode = self.mode
        lockdown_losses = self.config["lockdown_consecutive_losses"]
        defensive_losses = self.config["max_consecutive_losses"]
        max_drawdown = self.config["max_drawdown_pct"]

        if self.consecutive_losses >= lockdown_losses or self.total_drawdown >= max_drawdown:
            self.mode = RiskMode.LOCKDOWN
        elif self.consecutive_losses >= defensive_losses or self.daily_pnl <= -(self.capital * 0.024):
            self.mode = RiskMode.DEFENSIVE
        else:
            self.mode = RiskMode.NORMAL

        if prev_mode != self.mode:
            print(f"⚠️  風控模式切換：{prev_mode} → {self.mode}")

    def emergency_stop_all(self):
        self.emergency_stop = True
        print("🔴 緊急停止已啟動！所有交易暫停")

    def resume_trading(self):
        if self.mode != RiskMode.LOCKDOWN:
            self.emergency_stop = False
            print("✅ 恢復正常交易")
        else:
            print("⚠️  仍在 LOCKDOWN 模式，無法恢復")

    def daily_reset(self):
        self.daily_pnl = 0
        self.trades_today = []
        if self.mode == RiskMode.DEFENSIVE and self.consecutive_losses == 0:
            self.mode = RiskMode.NORMAL
            print("✅ 每日重置，風控模式恢復 NORMAL")

    def get_status(self):
        return {
            "mode": self.mode,
            "capital": round(self.capital, 2),
            "daily_pnl": round(self.daily_pnl, 2),
            "consecutive_losses": self.consecutive_losses,
            "total_drawdown": round(self.total_drawdown, 2),
            "emergency_stop": self.emergency_stop,
            "can_trade": self.check_can_trade()[0],
            "updated_at": datetime.now().isoformat()
        }

if __name__ == "__main__":
    rm = RiskManager(capital=10000)
    print("=== 初始狀態 ===")
    print(f"模式：{rm.mode}")
    can, reason = rm.check_can_trade()
    print(f"可以交易：{can}，原因：{reason}")

    qty, value = rm.calculate_position_size(price=500, confidence=75)
    print(f"\n=== 倉位計算 ===")
    print(f"建議數量：{qty} 股")
    print(f"建議金額：${value}")

    print(f"\n=== 模擬連續虧損 ===")
    for i in range(4):
        rm.update_after_trade(-200)
        print(f"第 {i+1} 次虧損後，模式：{rm.mode}")

    print(f"\n=== 緊急停止測試 ===")
    rm.emergency_stop_all()
    can, reason = rm.check_can_trade()
    print(f"可以交易：{can}，原因：{reason}")
