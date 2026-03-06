from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any, Protocol

from agents.data_agent import build_default_data_agent
from agents.strategy_agent.service import StrategyDecision, build_default_strategy_agent
from broker.alpaca_broker import AlpacaBroker
from config.settings import Settings, get_settings
from core.contracts.market_snapshot import LLMMarketSnapshot
from execution.order_executor import OrderExecutor
from logs.decision_logger import log_decision
from logs.trade_logger import log_trade
from metrics.performance_metrics import update_daily_metrics
from metrics.runtime_audit import update_runtime_audit
from portfolio.portfolio_manager import PortfolioManager
from risk.circuit_breaker import CircuitBreaker
from risk.risk_guard import RiskGuard
from risk.risk_manager import RiskManager
from state.market_cache import MarketStateCache
from state.portfolio_store import load_portfolio_state, save_portfolio_state
from utils.market_summary import build_market_summary


@dataclass
class TradingDecision:
    symbol: str
    action: str
    qty: int | None = None
    confidence: float | None = None
    rationale: str = ''
    meta: dict[str, Any] = field(default_factory=dict)

    def normalized_action(self) -> str:
        return self.action.strip().upper()


@dataclass
class TradingSymbolResult:
    symbol: str
    decision: str
    approved: bool
    risk_reason: str
    execution_status: str
    latest_price: float
    as_of: datetime


@dataclass
class TradingCycleReport:
    started_at: datetime
    finished_at: datetime
    results: list[TradingSymbolResult] = field(default_factory=list)
    portfolio_state: dict[str, Any] = field(default_factory=dict)
    next_check_minutes: int | None = None
    frequency_reason: str = ''


class DataSnapshotProvider(Protocol):
    def build_snapshot(self, symbol: str) -> LLMMarketSnapshot:
        ...


class LLMAgent(Protocol):
    def analyze(self, snapshot: LLMMarketSnapshot) -> TradingDecision:
        ...


class StrategyAgent(Protocol):
    def analyze(self, snapshot: LLMMarketSnapshot) -> StrategyDecision:
        ...

    def analyze_batch(self, snapshots: dict[str, LLMMarketSnapshot]) -> dict[str, StrategyDecision]:
        ...


class MarketAnalysisAgent(Protocol):
    def analyze(self, snapshot: LLMMarketSnapshot) -> Any:
        ...


class DecisionAgent(Protocol):
    def analyze(self, snapshot: LLMMarketSnapshot, market_analysis: Any) -> Any:
        ...


class DecisionRiskManager(Protocol):
    def validate(self, decision: TradingDecision, snapshot: LLMMarketSnapshot) -> tuple[bool, str]:
        ...


class RiskAgent(Protocol):
    def assess(self, snapshot: LLMMarketSnapshot, decision: TradingDecision) -> Any:
        ...


class TradingDecisionExecutor(Protocol):
    def execute(self, decision: TradingDecision, snapshot: LLMMarketSnapshot) -> str:
        ...


class PortfolioUpdater(Protocol):
    def update(self) -> dict[str, Any]:
        ...


class FrequencyAgent(Protocol):
    def recommend(
        self,
        results: list[dict[str, Any]],
        portfolio_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> Any:
        ...


class RiskGuardProtocol(Protocol):
    def validate(
        self,
        decision: Any,
        *,
        portfolio_state: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> Any:
        ...

    def record_trade(self, now: datetime | None = None) -> None:
        ...

    def update_after_cycle(self, portfolio_state: dict[str, Any], trades_executed: int, now: datetime | None = None) -> None:
        ...


class HeuristicLLMAgent:
    def analyze(self, snapshot: LLMMarketSnapshot) -> TradingDecision:
        indicators = snapshot.indicators
        sma_fast = indicators.get('sma_fast')
        sma_slow = indicators.get('sma_slow')

        if sma_fast is None or sma_slow is None:
            action = 'HOLD'
        elif sma_fast > sma_slow:
            action = 'BUY'
        elif sma_fast < sma_slow:
            action = 'SELL'
        else:
            action = 'HOLD'

        return TradingDecision(
            symbol=snapshot.symbol,
            action=action,
            confidence=0.5,
            rationale='Heuristic fallback based on moving-average relation',
            meta={'position_size': 0.1},
        )


class HeuristicMarketAnalysisAgent:
    def analyze(self, snapshot: LLMMarketSnapshot) -> dict[str, Any]:
        fast = snapshot.indicators.get('sma_fast')
        slow = snapshot.indicators.get('sma_slow')
        if fast is None or slow is None:
            trend = 'NEUTRAL'
        elif fast > slow:
            trend = 'BULLISH'
        elif fast < slow:
            trend = 'BEARISH'
        else:
            trend = 'NEUTRAL'

        return {
            'trend': trend,
            'momentum': float(snapshot.indicators.get('return_1', 0.0)),
            'volatility_regime': 'MEDIUM',
            'news_sentiment': 0.0,
            'summary': 'Heuristic analysis',
        }


class LegacyDecisionAgentAdapter:
    def __init__(self, llm_agent: LLMAgent):
        self.llm_agent = llm_agent

    def analyze(self, snapshot: LLMMarketSnapshot, market_analysis: Any) -> TradingDecision:
        return self.llm_agent.analyze(snapshot)


class DefaultDecisionRiskManager:
    def __init__(self, broker: AlpacaBroker, risk_manager: RiskManager):
        self.broker = broker
        self.risk_manager = risk_manager

    def validate(self, decision: TradingDecision, snapshot: LLMMarketSnapshot) -> tuple[bool, str]:
        action = decision.normalized_action()
        if action == 'HOLD':
            return False, 'HOLD_SIGNAL'
        if action not in {'BUY', 'SELL'}:
            return False, 'INVALID_ACTION'

        account = self.broker.get_account()
        start_equity = float(account.last_equity)
        current_equity = float(account.equity)
        if not self.risk_manager.check_drawdown(starting_equity=start_equity, current_equity=current_equity):
            return False, 'DRAWDOWN_LIMIT'

        open_orders = self.broker.list_open_orders()
        if self.risk_manager.has_duplicate_open_order(decision.symbol, action, open_orders):
            return False, 'DUPLICATE_ORDER'

        if decision.qty is None:
            cash = float(account.cash)
            decision.qty = self.risk_manager.calculate_order_qty(cash=cash, price=snapshot.latest_price)

        if not decision.qty or decision.qty <= 0:
            return False, 'INVALID_QTY'

        return True, 'APPROVED'


class LegacyRiskAgentAdapter:
    def __init__(self, risk_manager: DecisionRiskManager):
        self.risk_manager = risk_manager

    def assess(self, snapshot: LLMMarketSnapshot, decision: TradingDecision) -> dict[str, Any]:
        approved, reason = self.risk_manager.validate(decision, snapshot)
        return {
            'approved': approved,
            'reason': reason,
            'adjusted_action': decision.normalized_action(),
            'max_position_size': float(decision.meta.get('position_size', 1.0)),
        }


class FixedFrequencyAgent:
    def __init__(self, minutes: int = 5):
        self.minutes = max(1, int(minutes))

    def recommend(
        self,
        results: list[dict[str, Any]],
        portfolio_state: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {'next_check_minutes': self.minutes, 'reason': 'Default fixed interval'}


class DefaultTradingExecutor:
    def __init__(self, order_executor: OrderExecutor):
        self.order_executor = order_executor

    def execute(self, decision: TradingDecision, snapshot: LLMMarketSnapshot) -> str:
        return self.order_executor.execute_signal(
            symbol=decision.symbol,
            signal=decision.normalized_action(),
            latest_price=snapshot.latest_price,
        )


class DefaultPortfolioUpdater:
    def __init__(self, portfolio_manager: PortfolioManager):
        self.portfolio_manager = portfolio_manager

    def update(self) -> dict[str, Any]:
        return self.portfolio_manager.snapshot()


def run_cycle(
    symbols: list[str],
    *,
    data_agent: DataSnapshotProvider | None = None,
    strategy_agent: StrategyAgent | None = None,
    market_agent: MarketAnalysisAgent | None = None,
    decision_agent: DecisionAgent | None = None,
    risk_agent: RiskAgent | None = None,
    risk_guard: RiskGuardProtocol | None = None,
    frequency_agent: FrequencyAgent | None = None,
    llm_agent: LLMAgent | None = None,  # Legacy compatibility
    risk_manager: DecisionRiskManager | None = None,  # Legacy compatibility
    executor: TradingDecisionExecutor | None = None,
    portfolio_updater: PortfolioUpdater | None = None,
    system_guard: RiskGuardProtocol | None = None,  # Legacy compatibility alias
    settings: Settings | None = None,
) -> TradingCycleReport:
    logger = logging.getLogger('trading_orchestrator')
    started_at = datetime.now(timezone.utc)

    settings = settings or get_settings()
    dependencies = _build_default_dependencies(
        settings=settings,
        data_agent=data_agent,
        strategy_agent=strategy_agent,
        market_agent=market_agent,
        decision_agent=decision_agent,
        risk_agent=risk_agent,
        risk_guard=risk_guard or system_guard,
        frequency_agent=frequency_agent,
        llm_agent=llm_agent,
        risk_manager=risk_manager,
        executor=executor,
        portfolio_updater=portfolio_updater,
    )

    results: list[TradingSymbolResult] = []
    signal_rows: list[dict[str, Any]] = []
    executed_trades: list[dict[str, Any]] = []
    blocked_by_risk_guard = 0
    blocked_by_circuit_breaker = 0

    snapshots: dict[str, LLMMarketSnapshot] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for symbol in symbols:
        snapshot = dependencies['data_agent'].build_snapshot(symbol)
        snapshots[symbol] = snapshot
        summary = build_market_summary(snapshot)
        summaries[symbol] = summary
        log_decision(
            {
                'timestamp': snapshot.as_of,
                'symbol': symbol,
                'agent': 'market',
                'action': 'HOLD',
                'confidence': 0.0,
                'reason': f"summary={summary['trend']}/{summary['volatility']}/{summary['momentum']} volume_spike={summary['volume_spike']}",
                'price': snapshot.latest_price,
                'volatility': snapshot.indicators.get('volatility', 0.0),
            }
        )

    strategy_outputs: dict[str, Any] = {}
    pending_snapshots: dict[str, LLMMarketSnapshot] = {}
    reused_symbols: set[str] = set()
    strategy_mode = 'llm' if dependencies['strategy_agent'] is not None else 'fallback_legacy'
    for symbol, snapshot in snapshots.items():
        cached = dependencies['market_cache'].get_cached_decision(symbol, summaries[symbol]['volatility'])
        if cached is not None:
            strategy_outputs[symbol] = cached
            reused_symbols.add(symbol.upper())
        else:
            pending_snapshots[symbol] = snapshot

    strategy_agent_calls = 0
    strategy_symbols_sent = 0

    if pending_snapshots:
        if dependencies['strategy_agent'] is not None:
            strategy_agent_calls = 1
            strategy_symbols_sent = len(pending_snapshots)
            fresh = dependencies['strategy_agent'].analyze_batch(pending_snapshots)
            for symbol, output in fresh.items():
                strategy_outputs[symbol.upper()] = output
        else:
            for symbol, snapshot in pending_snapshots.items():
                market_analysis = dependencies['market_agent'].analyze(snapshot)
                strategy_outputs[symbol] = dependencies['decision_agent'].analyze(snapshot, market_analysis)

    prior_portfolio_state = load_portfolio_state()
    for symbol in symbols:
        snapshot = snapshots[symbol]
        summary = summaries[symbol]
        raw_output = strategy_outputs.get(symbol) or strategy_outputs.get(symbol.upper()) or {}
        decision = _decision_from_output(symbol=symbol, output=raw_output)
        market_state = str(_read_attr_or_key(raw_output, 'market_state', default=summary['trend']))

        if symbol.upper() not in reused_symbols:
            dependencies['market_cache'].update(
                symbol=symbol,
                volatility=summary['volatility'],
                decision_payload={
                    'symbol': symbol,
                    'market_state': market_state,
                    'action': decision.normalized_action(),
                    'confidence': float(decision.confidence or 0.0),
                    'position_size': float(decision.meta.get('position_size', 0.0) or 0.0),
                    'reason': decision.rationale or 'strategy decision',
                },
            )

        log_decision(
            {
                'timestamp': snapshot.as_of,
                'symbol': symbol,
                'agent': 'decision',
                'action': decision.normalized_action(),
                'confidence': decision.confidence or 0.0,
                'reason': f'market_state={market_state}; {decision.rationale}',
                'price': snapshot.latest_price,
                'volatility': snapshot.indicators.get('volatility', 0.0),
            }
        )

        if dependencies['risk_guard'] is not None:
            risk_check = dependencies['risk_guard'].validate(
                decision,
                portfolio_state=prior_portfolio_state,
                now=snapshot.as_of,
            )
            approved = bool(_read_attr_or_key(risk_check, 'approved', default=False))
            reason = str(_read_attr_or_key(risk_check, 'reason', default='RISK_GUARD_REJECTED'))
            decision.action = str(_read_attr_or_key(risk_check, 'action', default='HOLD'))
        else:
            risk_output = dependencies['risk_agent'].assess(snapshot, decision)
            approved, reason = _risk_result(risk_output)
            adjusted_action = str(_read_attr_or_key(risk_output, 'adjusted_action', default=decision.normalized_action()))
            decision.action = adjusted_action

        if not approved:
            reason_upper = reason.upper()
            if reason_upper.startswith('CIRCUIT_BREAKER'):
                blocked_by_circuit_breaker += 1
            elif dependencies['risk_guard'] is not None and reason_upper != 'HOLD_SIGNAL':
                blocked_by_risk_guard += 1

        log_decision(
            {
                'timestamp': snapshot.as_of,
                'symbol': symbol,
                'agent': 'risk',
                'action': decision.normalized_action(),
                'confidence': decision.confidence or 0.0,
                'reason': reason,
                'price': snapshot.latest_price,
                'volatility': snapshot.indicators.get('volatility', 0.0),
            }
        )

        if approved:
            execution_status = dependencies['executor'].execute(decision, snapshot)
            if not str(execution_status).upper().startswith('SKIPPED'):
                if dependencies['risk_guard'] is not None:
                    dependencies['risk_guard'].record_trade(now=snapshot.as_of)
                executed_trades.append(
                    {
                        'timestamp': snapshot.as_of,
                        'symbol': symbol,
                        'side': decision.normalized_action(),
                        'quantity': float(decision.qty or 0.0),
                        'price': snapshot.latest_price,
                    }
                )
        else:
            execution_status = 'SKIPPED_RISK_REJECTED'

        result = TradingSymbolResult(
            symbol=symbol,
            decision=decision.normalized_action(),
            approved=approved,
            risk_reason=reason,
            execution_status=execution_status,
            latest_price=snapshot.latest_price,
            as_of=snapshot.as_of,
        )
        results.append(result)
        signal_rows.append(
            {
                'symbol': symbol,
                'momentum': float(snapshot.indicators.get('return_1', 0.0)),
                'volatility': float(snapshot.indicators.get('volatility', 0.0)),
                'approved': approved,
                'executed': execution_status not in {'SKIPPED_RISK_REJECTED', 'SKIPPED_HOLD'},
            }
        )

        logger.info(
            'symbol=%s decision=%s approved=%s reason=%s execution=%s',
            symbol,
            decision.normalized_action(),
            approved,
            reason,
            execution_status,
        )

    portfolio_state = dependencies['portfolio_updater'].update()
    if dependencies['risk_guard'] is not None:
        dependencies['risk_guard'].update_after_cycle(
            portfolio_state=portfolio_state,
            trades_executed=len(executed_trades),
            now=datetime.now(timezone.utc),
        )
    persisted_portfolio_state = _build_persisted_portfolio_state(portfolio_state)
    save_portfolio_state(persisted_portfolio_state)

    for trade_event in executed_trades:
        log_trade(
            {
                **trade_event,
                'portfolio_cash': persisted_portfolio_state['cash'],
                'positions': persisted_portfolio_state['positions'],
            }
        )

    update_daily_metrics(
        cycle_time=datetime.now(timezone.utc),
        cycle_results=[_serialize_result(item) for item in results],
        portfolio_state=portfolio_state,
    )

    frequency_context = _build_frequency_context(signal_rows=signal_rows, portfolio_state=portfolio_state)
    next_check_minutes = 5
    frequency_reason = 'Fallback interval'
    frequency_agent_calls = 0
    frequency_fallback_used = False
    try:
        frequency_agent_calls = 1
        freq_output = _recommend_frequency(
            frequency_agent=dependencies['frequency_agent'],
            results=[_serialize_result(item) for item in results],
            portfolio_state=portfolio_state,
            context=frequency_context,
        )
        next_check_minutes = int(_read_attr_or_key(freq_output, 'next_check_minutes', default=5))
        if next_check_minutes < 1 or next_check_minutes > 15:
            raise ValueError('Frequency agent returned out-of-range next_check_minutes')
        frequency_reason = str(
            _read_attr_or_key(
                freq_output,
                'reason',
                default=_read_attr_or_key(freq_output, 'reasoning', default=''),
            )
        )
    except Exception as exc:
        next_check_minutes = 5
        frequency_reason = f'Fallback 5m: {exc}'
        frequency_fallback_used = True

    log_decision(
        {
            'timestamp': datetime.now(timezone.utc),
            'symbol': 'SYSTEM',
            'agent': 'frequency',
            'action': 'HOLD',
            'confidence': 0.0,
            'reason': frequency_reason,
            'price': 0.0,
            'volatility': frequency_context.get('avg_market_volatility', 0.0),
            'next_check_minutes': next_check_minutes,
        }
    )

    finished_at = datetime.now(timezone.utc)
    try:
        update_runtime_audit(
            cycle_time=finished_at,
            total_symbols=len(symbols),
            strategy_agent_calls=strategy_agent_calls,
            strategy_symbols_sent=strategy_symbols_sent,
            frequency_agent_calls=frequency_agent_calls,
            cache_hits=len(reused_symbols),
            trades_executed=len(executed_trades),
            blocked_by_risk_guard=blocked_by_risk_guard,
            blocked_by_circuit_breaker=blocked_by_circuit_breaker,
            next_check_minutes=next_check_minutes,
            fallback_used=frequency_fallback_used or strategy_mode != 'llm',
            strategy_mode=strategy_mode,
        )
    except Exception:
        logger.exception('Failed to update runtime audit report')

    return TradingCycleReport(
        started_at=started_at,
        finished_at=finished_at,
        results=results,
        portfolio_state=portfolio_state,
        next_check_minutes=next_check_minutes,
        frequency_reason=frequency_reason,
    )


def _build_default_dependencies(
    *,
    settings: Settings,
    data_agent: DataSnapshotProvider | None,
    strategy_agent: StrategyAgent | None,
    market_agent: MarketAnalysisAgent | None,
    decision_agent: DecisionAgent | None,
    risk_agent: RiskAgent | None,
    risk_guard: RiskGuardProtocol | None,
    frequency_agent: FrequencyAgent | None,
    llm_agent: LLMAgent | None,
    risk_manager: DecisionRiskManager | None,
    executor: TradingDecisionExecutor | None,
    portfolio_updater: PortfolioUpdater | None,
) -> dict[str, Any]:
    legacy_requested = any(
        [
            market_agent is not None,
            decision_agent is not None,
            risk_agent is not None,
            llm_agent is not None,
            risk_manager is not None,
        ]
    )
    if strategy_agent is None and not legacy_requested:
        try:
            strategy_agent = build_default_strategy_agent(model=settings.llm_strategy_model)
        except Exception:
            strategy_agent = None

    if llm_agent and not decision_agent:
        decision_agent = LegacyDecisionAgentAdapter(llm_agent)
    if risk_manager and not risk_agent:
        risk_agent = LegacyRiskAgentAdapter(risk_manager)

    if not decision_agent and not strategy_agent:
        decision_agent = LegacyDecisionAgentAdapter(HeuristicLLMAgent())

    requires_broker = (
        data_agent is None
        or executor is None
        or portfolio_updater is None
        or (risk_agent is None and risk_guard is None and risk_manager is None)
    )

    broker: AlpacaBroker | None = None
    base_risk_core: RiskManager | None = None
    default_risk_manager: DefaultDecisionRiskManager | None = None
    if requires_broker:
        broker = AlpacaBroker(settings)
        base_risk_core = RiskManager(
            max_position_pct=settings.max_position_pct,
            max_daily_drawdown_pct=settings.max_daily_drawdown_pct,
        )
        default_risk_manager = DefaultDecisionRiskManager(broker=broker, risk_manager=base_risk_core)

    if risk_guard is None and not legacy_requested:
        risk_guard = RiskGuard(circuit_breaker=CircuitBreaker())

    if risk_agent is None and default_risk_manager is not None:
        risk_agent = LegacyRiskAgentAdapter(default_risk_manager)

    if executor is None:
        if not broker or not base_risk_core:
            raise ValueError('executor is required when broker defaults are unavailable')
        order_executor = OrderExecutor(broker=broker, risk_manager=base_risk_core)
        executor = DefaultTradingExecutor(order_executor=order_executor)

    if portfolio_updater is None:
        if not broker:
            raise ValueError('portfolio_updater is required when broker defaults are unavailable')
        portfolio_manager = PortfolioManager(broker=broker)
        portfolio_updater = DefaultPortfolioUpdater(portfolio_manager=portfolio_manager)

    return {
        'data_agent': data_agent or build_default_data_agent(settings),
        'strategy_agent': strategy_agent,
        'market_agent': market_agent or HeuristicMarketAnalysisAgent(),
        'decision_agent': decision_agent or LegacyDecisionAgentAdapter(HeuristicLLMAgent()),
        'risk_agent': risk_agent,
        'risk_guard': risk_guard,
        'market_cache': MarketStateCache(),
        'frequency_agent': frequency_agent or FixedFrequencyAgent(minutes=5),
        'executor': executor,
        'portfolio_updater': portfolio_updater,
    }


def _decision_from_output(symbol: str, output: Any) -> TradingDecision:
    if isinstance(output, TradingDecision):
        output.symbol = symbol
        return output

    action = str(_read_attr_or_key(output, 'action', default='HOLD')).upper()
    confidence = _to_float_or_none(_read_attr_or_key(output, 'confidence', default=None))
    position_size = _to_float_or_none(_read_attr_or_key(output, 'position_size', default=None))
    reasoning = str(
        _read_attr_or_key(
            output,
            'reason',
            default=_read_attr_or_key(output, 'reasoning', default=''),
        )
    )
    market_state = str(_read_attr_or_key(output, 'market_state', default=''))

    return TradingDecision(
        symbol=symbol,
        action=action,
        confidence=confidence,
        rationale=reasoning,
        meta={
            'position_size': position_size if position_size is not None else 0.0,
            'market_state': market_state,
        },
    )


def _risk_result(risk_output: Any) -> tuple[bool, str]:
    approved = bool(_read_attr_or_key(risk_output, 'approved', default=False))
    reason = str(_read_attr_or_key(risk_output, 'reason', default='RISK_REJECTED'))
    return approved, reason


def _serialize_result(result: TradingSymbolResult) -> dict[str, Any]:
    return {
        'symbol': result.symbol,
        'decision': result.decision,
        'approved': result.approved,
        'risk_reason': result.risk_reason,
        'execution_status': result.execution_status,
        'latest_price': result.latest_price,
        'as_of': result.as_of.isoformat(),
    }


def _build_persisted_portfolio_state(portfolio_state: dict[str, Any]) -> dict[str, Any]:
    cash = _to_float_or_none(portfolio_state.get('cash'))
    realized = _to_float_or_none(portfolio_state.get('daily_pnl'))
    positions_map: dict[str, float] = {}
    unrealized_total = 0.0

    raw_positions = portfolio_state.get('positions', [])
    if isinstance(raw_positions, list):
        for row in raw_positions:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get('symbol', '')).upper()
            qty = _to_float_or_none(row.get('qty')) or 0.0
            if symbol:
                positions_map[symbol] = qty
            unrealized_total += _to_float_or_none(row.get('unrealized_pl')) or 0.0

    return {
        'cash': cash or 0.0,
        'positions': positions_map,
        'realized_pnl': realized or 0.0,
        'unrealized_pnl': unrealized_total,
    }


def _build_frequency_context(signal_rows: list[dict[str, Any]], portfolio_state: dict[str, Any]) -> dict[str, Any]:
    vol_values = [float(row.get('volatility', 0.0)) for row in signal_rows]
    momentum_values = [float(row.get('momentum', 0.0)) for row in signal_rows]
    executed_count = sum(1 for row in signal_rows if bool(row.get('executed')))

    avg_volatility = sum(vol_values) / len(vol_values) if vol_values else 0.0
    avg_momentum = sum(momentum_values) / len(momentum_values) if momentum_values else 0.0

    positions = portfolio_state.get('positions', [])
    open_positions = len(positions) if isinstance(positions, list) else 0

    return {
        'avg_market_volatility': avg_volatility,
        'avg_momentum': avg_momentum,
        'open_positions': open_positions,
        'recent_trade_activity': executed_count,
    }


def _recommend_frequency(
    frequency_agent: FrequencyAgent,
    results: list[dict[str, Any]],
    portfolio_state: dict[str, Any],
    context: dict[str, Any],
) -> Any:
    try:
        return frequency_agent.recommend(results=results, portfolio_state=portfolio_state, context=context)
    except TypeError:
        # Backward compatibility for older frequency agents with two-argument signature.
        return frequency_agent.recommend(results=results, portfolio_state=portfolio_state)


def _read_attr_or_key(obj: Any, name: str, default: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _to_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
