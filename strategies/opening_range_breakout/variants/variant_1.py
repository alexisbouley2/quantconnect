# region imports
from AlgorithmImports import *
# endregion

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Any
from tester import StrategyTester, Position

def opening_range_breakout(
    tester: StrategyTester,
    current_bars: Dict[str, Any],
    params: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Opening Range Breakout Strategy - Variant 1
    
    This strategy identifies momentum breakouts from the opening range (first N minutes)
    and uses a volatility-based trailing stop for exits.
    
    Variant 1: Reversion threshold based on opening range volatility
    - reversion_threshold = or_range * reversion_multiple
    - This makes the exit threshold proportional to the opening range volatility
    - More volatile opening ranges require larger reversions to trigger exits
    
    Strategy Logic:
    1. Calculate opening range (high/low) for first N minutes after market open
    2. Enter long when price breaks above: or_high + (or_range * breakout_buffer)
    3. Enter short when price breaks below: or_low - (or_range * breakout_buffer)
    4. Exit via trailing stop: reversion from high_water_mark by (or_range * reversion_multiple)
    5. Force exit at specified time (e.g., 15:45) to avoid overnight risk
    
    Args:
        tester: StrategyTester instance providing backtesting infrastructure
        current_bars: Dictionary mapping symbol -> current bar data
        params: Strategy parameters dictionary with keys:
            - opening_range_minutes (int): Duration of opening range in minutes (default: 30)
            - breakout_buffer (float): Multiplier for breakout threshold (default: 0.2)
            - reversion_multiple (float): Exit threshold as multiple of OR range (default: 0.5)
            - exit_time (str): Time to force exit in 'HH:MM' format (default: '15:30')
            - max_positions (int): Maximum concurrent positions (default: 3)
                                    Cash allocation per position = 1.0 / max_positions
    
    Returns:
        List of order dictionaries, each with keys: symbol, action, price, cash_allocation, metadata
    
    Example:
        >>> params = {
        ...     'opening_range_minutes': 30,
        ...     'breakout_buffer': 0.2,
        ...     'reversion_multiple': 0.5,
        ...     'exit_time': '15:30',
        ...     'max_positions': 3
        ... }
        >>> orders = opening_range_breakout(tester, current_bars, params)
    """
    orders: List[Dict[str, Any]] = []
    
    # Extract and validate parameters
    opening_range_minutes: int = int(params.get('opening_range_minutes', 30))
    breakout_buffer: float = params.get('breakout_buffer', 0.2)
    reversion_multiple: float = params.get('reversion_multiple', 0.5)
    exit_time_str: str = params.get('exit_time', '15:30')
    max_positions: int = int(params.get('max_positions', 3))
    
    # Parse exit time
    exit_hour, exit_min = map(int, exit_time_str.split(':'))
    exit_time: time = time(exit_hour, exit_min)
    
    # Calculate cash allocation per position (equal weighting)
    cash_allocation: float = 1.0 / max_positions
    
    # Calculate opening range end time (market open + opening_range_minutes)
    market_open: time = time(9, 30)
    opening_range_end: time = (
        datetime.combine(datetime.today(), market_open) + 
        timedelta(minutes=opening_range_minutes)
    ).time()
    
    # Track symbols already traded today (prevents re-entry on same trading day)
    current_date = tester.current_time.date() if tester.current_time else None
    if not hasattr(tester, '_traded_symbols_today') or tester._traded_symbols_today.get('date') != current_date:
        tester._traded_symbols_today = {'date': current_date, 'symbols': set()}
    traded_today: set = tester._traded_symbols_today['symbols']
    
    # Process each symbol's current bar
    for symbol, bar in current_bars.items():
        # Get current bar time
        current_time = bar.name.time() if hasattr(bar.name, 'time') else tester.current_time.time()
        
        # Skip if still in opening range period (wait for range to be established)
        if current_time <= opening_range_end:
            continue
        
        # Calculate opening range (high/low) for today
        hist_data = tester.get_historical_data(symbol)
        today_data = hist_data[hist_data['date'] == bar['date']]
        or_data = today_data[today_data['time'] <= opening_range_end]
        
        # Skip if insufficient data for opening range calculation
        if len(or_data) == 0:
            continue
        
        # Extract opening range statistics
        or_high: float = or_data['high'].max()
        or_low: float = or_data['low'].min()
        or_range: float = or_high - or_low
        
        # Calculate breakout thresholds (with buffer multiplier)
        breakout_long: float = or_high + (or_range * breakout_buffer)
        breakout_short: float = or_low - (or_range * breakout_buffer)
        
        # Get current position for this symbol (if any)
        position: Optional[Position] = tester.get_position(symbol)
        
        # Force exit at end of day (time-based exit to avoid overnight risk)
        if current_time >= exit_time and position:
            orders.append({
                'symbol': symbol,
                'action': 'close',
                'price': bar['close'],
                'metadata': {'exit_reason': 'time_exit'}
            })
            traded_today.add(symbol)  # Mark as traded today (prevents re-entry)
            continue
        
        # Skip entry if past exit time (prevents entering positions too late in day)
        if current_time >= exit_time:
            continue
        
        # Entry logic: Check for breakout signals
        if not position:
            # Skip if already traded this symbol today (one trade per symbol per day)
            if symbol in traded_today:
                continue
            
            # Check position limit: Skip if already at maximum concurrent positions
            open_positions_count: int = tester.get_open_positions_count()
            if open_positions_count >= max_positions:
                continue  # Skip this signal, portfolio is at capacity
            
            # Prepare order dictionary with position metadata
            order_dict: Dict[str, Any] = {
                'symbol': symbol,
                'price': bar['close'],
                'cash_allocation': cash_allocation,
                'metadata': {
                    'or_high': or_high,
                    'or_low': or_low,
                    'or_range': or_range,
                    'high_water_mark': bar['close']  # Track peak for trailing stop
                }
            }
            
            # Long entry: Price breaks above upper breakout threshold
            if bar['close'] > breakout_long:
                order_dict['action'] = 'buy'
                orders.append(order_dict.copy())
                traded_today.add(symbol)
            
            # Short entry: Price breaks below lower breakout threshold
            elif bar['close'] < breakout_short:
                order_dict['action'] = 'sell'
                orders.append(order_dict.copy())
                traded_today.add(symbol)
        
        # Exit logic: Trailing stop based on opening range volatility (Variant 1)
        else:
            metadata: Dict[str, Any] = position.metadata
            
            # Variant 1: Reversion threshold = opening_range * reversion_multiple
            # This makes the stop proportional to the day's opening volatility
            reversion_threshold: float = metadata['or_range'] * reversion_multiple
            
            if position.direction == 'long':
                # Update high water mark (trailing stop only moves up)
                if bar['close'] > metadata['high_water_mark']:
                    tester.update_position_metadata(symbol, {'high_water_mark': bar['close']})
                    metadata['high_water_mark'] = bar['close']
                
                # Check if price has reverted from high water mark by threshold
                reversion_level: float = metadata['high_water_mark'] - reversion_threshold
                if bar['close'] < reversion_level:
                    orders.append({
                        'symbol': symbol,
                        'action': 'close',
                        'price': bar['close'],
                        'metadata': {'exit_reason': 'reversion'}
                    })
                    traded_today.add(symbol)
            
            else:  # short position
                # Update low water mark (trailing stop only moves down)
                # Note: Using high_water_mark in metadata for both long/short for simplicity
                # For shorts, it represents the lowest price (best entry point)
                if bar['close'] < metadata['high_water_mark']:
                    tester.update_position_metadata(symbol, {'high_water_mark': bar['close']})
                    metadata['high_water_mark'] = bar['close']
                
                # Check if price has reverted from low water mark by threshold
                reversion_level = metadata['high_water_mark'] + reversion_threshold
                if bar['close'] > reversion_level:
                    orders.append({
                        'symbol': symbol,
                        'action': 'close',
                        'price': bar['close'],
                        'metadata': {'exit_reason': 'reversion'}
                    })
                    traded_today.add(symbol)
    
    return orders


# ===== USAGE EXAMPLE =====
# from tester import StrategyTester
# from strategies.opening_range_breakout.variant_1 import opening_range_breakout
#
# tester = StrategyTester(
#     symbols=['SPY'],
#     start_date=(2023, 1, 1),
#     end_date=(2024, 1, 1),
#     initial_cash=10000,
#     resolution='minute',
#     benchmark_symbol='SPY'  # Optional: compare to benchmark
# )
#
# params = {
#     'opening_range_minutes': 30,
#     'breakout_buffer': 0.2,
#     'reversion_multiple': 0.5,
#     'exit_time': '15:30',
#     'max_positions': 3  # Allocates 1/3 of cash per position
# }
#
# tester.run(opening_range_breakout, params)
# stats = tester.get_stats(plot=True)
# tester.print_stats(stats)

