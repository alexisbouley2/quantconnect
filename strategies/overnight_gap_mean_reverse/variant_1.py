# region imports
from AlgorithmImports import *
# endregion

from datetime import datetime, time, timedelta
import pandas as pd
import numpy as np

def overnight_gap_mean_reverse(tester, current_bars, params):
    """
    Overnight gap mean reversion strategy
    
    Identifies unusual overnight gaps and bets on mean reversion:
    - Unusual gap = abs(gap) > sigma * volatility (rolling standard deviation of prices)
    - For upward gaps (price gap up), take short position (bet on reversion down)
    - For downward gaps (price gap down), take long position (bet on reversion up)
    - Enter at 9:31, exit at market open (9:30) + exit_minutes_after_open
    
    Params:
        - volatility_window: Number of periods for rolling volatility calculation (default: 60)
        - sigma: Multiplier for what constitutes an unusual gap (default: 3.0)
        - exit_minutes_after_open: Minutes after market open to close positions (default: 45)
    """
    orders = []
    
    volatility_window = int(params.get('volatility_window', 60))
    sigma = params.get('sigma', 3.0)
    exit_minutes_after_open = int(params.get('exit_minutes_after_open', 45))
    
    market_open = time(9, 30)
    entry_time = time(9, 31)  # 1 minute after market open
    market_close = time(16, 0)
    exit_time = (datetime.combine(datetime.today(), market_open) + 
                 timedelta(minutes=exit_minutes_after_open)).time()
    
    # Initialize storage for tracking previous closes and price history
    if not hasattr(tester, '_gap_strategy_data'):
        tester._gap_strategy_data = {
            'previous_close': {},      # symbol -> last close price
            'price_history': {}        # symbol -> list of close prices for volatility calculation
        }
    
    gap_data = tester._gap_strategy_data
    previous_close = gap_data['previous_close']
    price_history = gap_data['price_history']
    
    current_time_obj = tester.current_time.time()
    
    
    # Update previous close at market close
    if current_time_obj == market_close:
        for symbol, bar in current_bars.items():
            previous_close[symbol] = bar['close']
    
    # Exit logic: Close all positions at exit time
    if current_time_obj >= exit_time:
        for symbol, bar in current_bars.items():
            if tester.has_position(symbol):
                orders.append({
                    'symbol': symbol,
                    'action': 'close',
                    'price': bar['close']
                })
    
    # Entry logic: At 9:31, find all symbols with unusual gaps and enter positions
    # Check if we're at entry time (9:31) - allow for slight timing differences
    is_entry_time = (entry_time <= current_time_obj < time(9, 32))
    
    if is_entry_time:
        qualifying_symbols = []  # List of (symbol, bar, gap, action)
        
        for symbol, bar in current_bars.items():
            # Skip if already have position
            if tester.has_position(symbol):
                continue
            
            # Check if we have previous day's close
            if symbol not in previous_close or previous_close[symbol] is None:
                continue
            
            # Calculate gap: today's open - yesterday's close
            today_open = bar['open']
            gap = today_open - previous_close[symbol]
            
            # Calculate volatility from price history (rolling standard deviation of closes)
            if symbol not in price_history or len(price_history[symbol]) < 2:
                continue
            
            volatility = np.std(price_history[symbol])
            
            if volatility is None or volatility <= 0:
                continue


            if abs(gap) > sigma * volatility:
                # Determine action based on gap direction
                if gap > 0:
                    # Upward gap - short position (bet on reversion down)
                    action = 'sell'
                else:
                    # Downward gap - long position (bet on reversion up)
                    action = 'buy'
                
                qualifying_symbols.append((symbol, bar, gap, action, volatility))
        
        # Allocate cash equally among all qualifying symbols
        if qualifying_symbols:
            num_positions = len(qualifying_symbols)
            cash_allocation = 1.0 / num_positions
            
            for symbol, bar, gap, action, volatility in qualifying_symbols:
                orders.append({
                    'symbol': symbol,
                    'action': action,
                    'price': bar['open'],
                    'cash_allocation': cash_allocation,
                    'metadata': {
                        'gap': gap,
                        'volatility': volatility,
                        'previous_close': previous_close[symbol]
                    }
                })
    
    for symbol, bar in current_bars.items():
        if symbol not in price_history:
            price_history[symbol] = []
        price_history[symbol].append(bar['close'])
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
