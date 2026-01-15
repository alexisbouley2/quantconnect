# region imports
from AlgorithmImports import *
# endregion

def opening_range_breakout_strategy(tester, current_bars, params):
    """
    Opening range breakout strategy
    
    Params:
        - opening_range_minutes: Duration of opening range
        - breakout_buffer: Buffer as fraction of OR range
        - reversion_multiple: Exit threshold as multiple of OR range
        - exit_time: Time to force exit
    """
    orders = []
    
    opening_range_minutes = params.get('opening_range_minutes', 30)
    breakout_buffer = params.get('breakout_buffer', 0.2)
    reversion_multiple = params.get('reversion_multiple', 0.5)
    exit_time_str = params.get('exit_time', '15:30')
    exit_hour, exit_min = map(int, exit_time_str.split(':'))
    exit_time = time(exit_hour, exit_min)
    
    market_open = time(9, 30)
    opening_range_end = (datetime.combine(datetime.today(), market_open) + 
                         timedelta(minutes=opening_range_minutes)).time()
    
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
            continue
        
        # Entry logic
        if not position:
            if bar['close'] > breakout_long:
                orders.append({
                    'symbol': symbol,
                    'action': 'buy',
                    'price': bar['close'],
                    'metadata': {
                        'or_high': or_high,
                        'or_low': or_low,
                        'or_range': or_range,
                        'high_water_mark': bar['close']
                    }
                })
            elif bar['close'] < breakout_short:
                orders.append({
                    'symbol': symbol,
                    'action': 'sell',
                    'price': bar['close'],
                    'metadata': {
                        'or_high': or_high,
                        'or_low': or_low,
                        'or_range': or_range,
                        'high_water_mark': bar['close']
                    }
                })
        
        # Exit logic
        else:
            metadata = position.metadata
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
    
    return orders



# ===== USAGE EXAMPLE =====
# from tester import StrategyTester
# from strategies.opening_range_breakout_strategy import opening_range_breakout_strategy

# Single backtest
# tester = StrategyTester(
#     symbols=['SPY'],
#     start_date=(2023, 1, 1),
#     end_date=(2024, 1, 1),
#     initial_cash=10000,
#     resolution='minute'
# )

# params = {
#     'opening_range_minutes': 30,
#     'breakout_buffer': 0.2,
#     'reversion_multiple': 0.5,
#     'exit_time': '15:30'
# }

# tester.run(opening_range_breakout_strategy, params)
# stats = tester.get_stats(plot=True)
# tester.print_stats(stats)