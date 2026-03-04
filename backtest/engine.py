from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from backtest.models import BacktestReport, Bar, EquityPoint
from backtest.performance import max_drawdown, sharpe_ratio
from backtest.simulated_broker import SimulatedBroker
from risk.risk_manager import RiskManager


class BacktestEngine:
    """
    Runs historical simulation with live-like semantics:
    - signals generated on bar close
    - market orders filled on next bar open
    """

    def __init__(
        self,
        strategy,
        risk_manager: RiskManager,
        initial_cash: float = 100_000.0,
    ):
        self.strategy = strategy
        self.risk_manager = risk_manager
        self.broker = SimulatedBroker(initial_cash=initial_cash)

    def run(self, bars_by_symbol: dict[str, list[Bar]]) -> BacktestReport:
        self._validate_input(bars_by_symbol)
        timestamps = [bar.timestamp for bar in next(iter(bars_by_symbol.values()))]

        close_history: dict[str, list[float]] = defaultdict(list)
        equity_curve: list[EquityPoint] = []

        for i, ts in enumerate(timestamps):
            close_prices: dict[str, float] = {}

            for symbol, series in bars_by_symbol.items():
                bar = series[i]
                self.broker.fill_orders_for_open(symbol=symbol, ts=bar.timestamp, open_price=bar.open)
                close_history[symbol].append(bar.close)
                close_prices[symbol] = bar.close

            for symbol, closes in close_history.items():
                signal_result = self.strategy.generate_signal(symbol=symbol, closes=closes)
                self._handle_signal(symbol=symbol, signal=signal_result.signal, close_price=closes[-1], ts=ts)

            equity = self.broker.mark_to_market(close_prices=close_prices)
            equity_curve.append(EquityPoint(timestamp=ts, equity=equity, cash=self.broker.cash))

        return BacktestReport(
            equity_curve=equity_curve,
            trade_log=self.broker.filled_trades,
            max_drawdown=max_drawdown(equity_curve),
            sharpe_ratio=sharpe_ratio(equity_curve),
        )

    def _handle_signal(self, symbol: str, signal: str, close_price: float, ts: datetime) -> None:
        if signal == 'HOLD':
            return

        account = self.broker.get_account()
        if not self.risk_manager.check_drawdown(
            starting_equity=float(account.last_equity),
            current_equity=float(account.equity),
        ):
            return

        if self.risk_manager.has_duplicate_open_order(symbol, signal, self.broker.list_open_orders()):
            return

        qty = self.risk_manager.calculate_order_qty(cash=float(account.cash), price=close_price)
        if qty <= 0:
            return

        self.broker.place_market_order(symbol=symbol, qty=qty, side=signal, submitted_at=ts)

    @staticmethod
    def _validate_input(bars_by_symbol: dict[str, list[Bar]]) -> None:
        if not bars_by_symbol:
            raise ValueError('bars_by_symbol must not be empty')

        expected_timestamps: list[datetime] | None = None
        for symbol, bars in bars_by_symbol.items():
            if not bars:
                raise ValueError(f'no bars provided for {symbol}')
            timestamps = [bar.timestamp for bar in bars]
            if expected_timestamps is None:
                expected_timestamps = timestamps
            elif timestamps != expected_timestamps:
                raise ValueError('all symbols must share identical timestamp index for deterministic replay')
