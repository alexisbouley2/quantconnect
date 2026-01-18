# region imports
from AlgorithmImports import *
# endregion

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any
from tester import StrategyTester
import numpy as np

def overnight_gap_mean_reverse(
    tester: StrategyTester,
    current_bars: Dict[str, Any],
    params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Overnight Gap Mean Reversion Strategy
    
    This strategy identifies unusual overnight price gaps and bets on mean reversion.
    The hypothesis is that large overnight gaps (caused by after-hours news, wider spreads,
    or emergency trading needs) tend to revert during regular market hours.
    
    Strategy Logic:
    1. Calculate gap: today's open - yesterday's close
    2. Calculate volatility: rolling standard deviation of price closes
    3. Identify unusual gaps: abs(gap) > sigma * volatility (where sigma is a multiplier)
    4. Entry: At 9:31 AM (1 minute after market open)
       - Upward gaps → Short position (bet on reversion down)
       - Downward gaps → Long position (bet on reversion up)
    5. Exit: At market open + exit_minutes_after_open (e.g., 9:45 AM)
    
    Args:
        tester: StrategyTester instance providing backtesting infrastructure
        current_bars: Dictionary mapping symbol -> current bar data
        params: Strategy parameters dictionary with keys:
            - volatility_window (int): Number of periods for rolling volatility calculation (default: 60)
            - sigma (float): Multiplier for what constitutes an unusual gap (default: 3.0)
            - exit_minutes_after_open (int): Minutes after market open to close positions (default: 45)
    
    Returns:
        List of order dictionaries, each with keys: symbol, action, price, cash_allocation, metadata
    
    Example:
        >>> params = {
        ...     'volatility_window': 60,
        ...     'sigma': 10.0,
        ...     'exit_minutes_after_open': 15
        ... }
        >>> orders = overnight_gap_mean_reverse(tester, current_bars, params)
    """
    orders: List[Dict[str, Any]] = []
    
    # Extract and validate parameters
    volatility_window: int = int(params.get('volatility_window', 60))
    sigma: float = params.get('sigma', 3.0)
    exit_minutes_after_open: int = int(params.get('exit_minutes_after_open', 45))
    
    # Define market timing constants
    market_open: time = time(9, 30)
    entry_time: time = time(9, 31)  # 1 minute after market open (allows market to open)
    market_close: time = time(16, 0)
    exit_time: time = (
        datetime.combine(datetime.today(), market_open) + 
        timedelta(minutes=exit_minutes_after_open)
    ).time()
    
    # Initialize storage for tracking previous closes and price history
    # This persists across time steps within the same backtest
    if not hasattr(tester, '_gap_strategy_data'):
        tester._gap_strategy_data = {
            'previous_close': {},      # symbol -> last close price (updated at market close)
            'price_history': {}        # symbol -> list of close prices for volatility calculation
        }
    
    gap_data: Dict[str, Any] = tester._gap_strategy_data
    previous_close: Dict[str, float] = gap_data['previous_close']
    price_history: Dict[str, List[float]] = gap_data['price_history']
    
    # Get current bar time
    current_time_obj: time = tester.current_time.time()
    
    # Update previous close at market close (for gap calculation tomorrow)
    if current_time_obj == market_close:
        for symbol, bar in current_bars.items():
            previous_close[symbol] = bar['close']
    
    # Exit logic: Close all positions at exit time (time-based exit)
    # This limits intraday exposure and prevents holding positions too long
    if current_time_obj >= exit_time:
        for symbol, bar in current_bars.items():
            if tester.has_position(symbol):
                orders.append({
                    'symbol': symbol,
                    'action': 'close',
                    'price': bar['close']
                })
    
    # Entry logic: At 9:31, identify all symbols with unusual gaps and enter positions
    # Check if we're at entry time (9:31) - allow for slight timing differences (1-minute window)
    is_entry_time: bool = (entry_time <= current_time_obj < time(9, 32))
    
    if is_entry_time:
        qualifying_symbols: List[tuple] = []  # List of (symbol, bar, gap, action, volatility)
        
        # First pass: Identify all symbols with unusual gaps
        for symbol, bar in current_bars.items():
            # Skip if already have position (one trade per symbol per day)
            if tester.has_position(symbol):
                continue
            
            # Check if we have previous day's close (required for gap calculation)
            if symbol not in previous_close or previous_close[symbol] is None:
                continue
            
            # Calculate gap: today's open - yesterday's close
            today_open: float = bar['open']
            gap: float = today_open - previous_close[symbol]
            
            # Calculate volatility from price history (rolling standard deviation of closes)
            # Need at least 2 data points for standard deviation calculation
            if symbol not in price_history or len(price_history[symbol]) < 2:
                continue
            
            volatility: float = np.std(price_history[symbol])
            
            # Skip if volatility is invalid (zero or negative)
            if volatility is None or volatility <= 0:
                continue

            # Check if gap is unusual: abs(gap) > sigma * volatility
            # This filters for gaps that are statistically significant (sigma standard deviations)
            if abs(gap) > sigma * volatility:
                # Determine action based on gap direction (mean reversion hypothesis)
                if gap > 0:
                    # Upward gap → Short position (bet on reversion down)
                    action: str = 'sell'
                else:
                    # Downward gap → Long position (bet on reversion up)
                    action = 'buy'
                
                qualifying_symbols.append((symbol, bar, gap, action, volatility))
        
        # Second pass: Allocate cash equally among all qualifying symbols
        if qualifying_symbols:
            num_positions: int = len(qualifying_symbols)
            cash_allocation: float = 1.0 / num_positions  # Equal weighting
            
            # Enter positions for all qualifying symbols simultaneously
            for symbol, bar, gap, action, volatility in qualifying_symbols:
                orders.append({
                    'symbol': symbol,
                    'action': action,
                    'price': bar['open'],  # Enter at opening price
                    'cash_allocation': cash_allocation,
                    'metadata': {
                        'gap': gap,
                        'volatility': volatility,
                        'previous_close': previous_close[symbol],
                        'sigma_threshold': sigma * volatility
                    }
                })
    
    # Update price history for volatility calculation (maintain rolling window)
    # This runs every bar to keep volatility estimate current
    for symbol, bar in current_bars.items():
        if symbol not in price_history:
            price_history[symbol] = []
        price_history[symbol].append(bar['close'])
        
        # Maintain rolling window: keep only last volatility_window prices
        if len(price_history[symbol]) > volatility_window:
            price_history[symbol] = price_history[symbol][-volatility_window:]
            
    return orders


# ===== USAGE EXAMPLE =====
# from tester import StrategyTester
# from strategies.overnight_gap_mean_reverse.variant_1 import overnight_gap_mean_reverse
#
# tester = StrategyTester(
#     symbols=['TSLA', 'SPY', 'QQQ'],
#     start_date=(2023, 1, 1),
#     end_date=(2024, 1, 1),
#     initial_cash=10000,
#     resolution='minute',
#     benchmark_symbol='SPY'  # Optional: compare to benchmark
# )
#
# params = {
#     'volatility_window': 60,      # 60 periods rolling window for volatility
#     'sigma': 3.0,                  # 3 standard deviations for unusual gap
#     'exit_minutes_after_open': 45 # Close positions at 10:15 (9:30 + 45 minutes)
# }
#
# tester.run(overnight_gap_mean_reverse, params)
# stats = tester.get_stats(plot=True)
# tester.print_stats(stats)
