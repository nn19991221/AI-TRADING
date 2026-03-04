from __future__ import annotations


class RiskManager:
    """Basic risk checks: sizing, duplicate orders, and drawdown protection."""

    def __init__(self, max_position_pct: float, max_daily_drawdown_pct: float):
        self.max_position_pct = max_position_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct

    def check_drawdown(self, starting_equity: float, current_equity: float) -> bool:
        if starting_equity <= 0:
            return False
        drawdown = (starting_equity - current_equity) / starting_equity
        return drawdown <= self.max_daily_drawdown_pct

    def has_duplicate_open_order(self, symbol: str, side: str, open_orders: list) -> bool:
        for order in open_orders:
            if order.symbol == symbol and str(order.side).upper().endswith(side.upper()):
                return True
        return False

    def calculate_order_qty(self, cash: float, price: float) -> int:
        if price <= 0:
            return 0
        budget = cash * self.max_position_pct
        qty = int(budget // price)
        return max(qty, 0)
