# region imports
from AlgorithmImports import *
# endregion

from datetime import datetime, time, timedelta

def opening_range_breakout_strategy(tester, current_bars, params):
    """
    Opening range breakout strategy - Variant 1
    
    Reversion threshold based on opening range volatility:
    reversion_threshold = or_range * reversion_multiple
    
    This variant uses a fixed volatility measure (opening range) to determine
    when to exit, making it proportional to the opening range volatility.
    
    Params:
        - opening_range_minutes: Duration of opening range
        - breakout_buffer: Buffer as fraction of OR range
        - reversion_multiple: Exit threshold as multiple of OR range
        - exit_time: Time to force exit (e.g., '15:30')
        - max_positions: Maximum number of concurrent positions (default: 3)
          Cash allocation per position = available_cash / max_positions
    """
    orders = []
    
    opening_range_minutes = int(params.get('opening_range_minutes', 30))
    breakout_buffer = params.get('breakout_buffer', 0.2)
    reversion_multiple = params.get('reversion_multiple', 0.5)
    exit_time_str = params.get('exit_time', '15:30')
    max_positions = int(params.get('max_positions', 3))
    exit_hour, exit_min = map(int, exit_time_str.split(':'))
    exit_time = time(exit_hour, exit_min)
    
    # Calculate cash allocation per position
    cash_allocation = 1.0 / max_positions
    
    market_open = time(9, 30)
    opening_range_end = (datetime.combine(datetime.today(), market_open) + 
                         timedelta(minutes=opening_range_minutes)).time()
    
    # Track symbols already traded today (to prevent re-entry on same day)
    current_date = tester.current_time.date() if tester.current_time else None
    if not hasattr(tester, '_traded_symbols_today') or tester._traded_symbols_today.get('date') != current_date:
        tester._traded_symbols_today = {'date': current_date, 'symbols': set()}
    traded_today = tester._traded_symbols_today['symbols']
    
    for symbol, bar in current_bars.items():
        current_time = bar.name.time() if hasattr(bar.name, 'time') else tester.current_time.time()
        
        # Skip opening range period
        if current_time <= opening_range_end:
            continue
        
        # Calculate opening range (once per day)
        hist_data = tester.get_historical_data(symbol)
        today_data = hist_data[hist_data['date'] == bar['date']]
        or_data = today_data[today_data['time'] <= opening_range_end]
        
        if len(or_data) == 0:
            continue
        
        or_high = or_data['high'].max()
        or_low = or_data['low'].min()
        or_range = or_high - or_low
        
        breakout_long = or_high + (or_range * breakout_buffer)
        breakout_short = or_low - (or_range * breakout_buffer)
        
        position = tester.get_position(symbol)
        
        # Force exit at end of day
        if current_time >= exit_time and position:
            orders.append({
                'symbol': symbol,
                'action': 'close',
                'price': bar['close'],
                'metadata': {'exit_reason': 'time_exit'}
            })
            traded_today.add(symbol)  # Mark as traded today (prevents re-entry)
            continue
        
        # Skip entry if past exit time (prevent re-entry after exit)
        if current_time >= exit_time:
            continue
        
        # Entry logic
        if not position:
            # Skip if we've already traded this symbol today (prevent re-entry)
            if symbol in traded_today:
                continue
            
            # Check if we're at max positions limit
            open_positions_count = tester.get_open_positions_count()
            if open_positions_count >= max_positions:
                continue  # Skip this signal, already at max positions
            
            # Build order dict with position sizing (strategy controls this)
            order_dict = {
                'symbol': symbol,
                'price': bar['close'],
                'cash_allocation': cash_allocation,
                'metadata': {
                    'or_high': or_high,
                    'or_low': or_low,
                    'or_range': or_range,
                    'high_water_mark': bar['close']
                }
            }
            
            if bar['close'] > breakout_long:
                order_dict['action'] = 'buy'
                orders.append(order_dict.copy())
                traded_today.add(symbol)  # Mark as traded today
            elif bar['close'] < breakout_short:
                order_dict['action'] = 'sell'
                orders.append(order_dict.copy())
                traded_today.add(symbol)  # Mark as traded today
        
        # Exit logic
        else:
            metadata = position.metadata
            # Variant 1: Reversion threshold based on opening range volatility
            reversion_threshold = metadata['or_range'] * reversion_multiple
            
            if position.direction == 'long':
                # Update high water mark
                if bar['close'] > metadata['high_water_mark']:
                    tester.update_position_metadata(symbol, {'high_water_mark': bar['close']})
                    metadata['high_water_mark'] = bar['close']
                
                # Check reversion
                reversion_level = metadata['high_water_mark'] - reversion_threshold
                if bar['close'] < reversion_level:
                    orders.append({
                        'symbol': symbol,
                        'action': 'close',
                        'price': bar['close'],
                        'metadata': {'exit_reason': 'reversion'}
                    })
                    traded_today.add(symbol)  # Mark as traded today (prevents re-entry)
            
            else:  # short
                # Update low water mark
                if bar['close'] < metadata['high_water_mark']:
                    tester.update_position_metadata(symbol, {'high_water_mark': bar['close']})
                    metadata['high_water_mark'] = bar['close']
                
                # Check reversion
                reversion_level = metadata['high_water_mark'] + reversion_threshold
                if bar['close'] > reversion_level:
                    orders.append({
                        'symbol': symbol,
                        'action': 'close',
                        'price': bar['close'],
                        'metadata': {'exit_reason': 'reversion'}
                    })
                    traded_today.add(symbol)  # Mark as traded today (prevents re-entry)
    
    return orders


# ===== USAGE EXAMPLE =====
# from tester import StrategyTester
# from strategies.opening_range_breakout_strategy.variant_1 import opening_range_breakout_strategy
#
# tester = StrategyTester(
#     symbols=['SPY'],
#     start_date=(2023, 1, 1),
#     end_date=(2024, 1, 1),
#     initial_cash=10000,
#     resolution='minute'
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
# tester.run(opening_range_breakout_strategy, params)
# stats = tester.get_stats(plot=True)
# tester.print_stats(stats)

