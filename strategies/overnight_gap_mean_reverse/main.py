# region imports
from AlgorithmImports import *
# endregion

import numpy as np
class FadingTheGap(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2018, 1, 1)
        self.set_end_date(2019, 1, 1)
        self.set_cash(100000)

        self.sigma = 10.0
        self.close_positions_minutes = 15
        self.volatility_window = 60
        

        # Major indices (highly liquid)
        etfs = ['SPY', 'QQQ', 'IWM', 'DIA']

        # Top S&P 500 stocks by liquidity
        sp500_leaders = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 
                        'BRK.B', 'V', 'XOM', 'JNJ', 'JPM', 'WMT', 'MA', 'PG',
                        'UNH', 'HD', 'DIS', 'BAC', 'VZ', 'ADBE', 'CRM', 'CVX',
                        'NFLX', 'COST', 'ABBV', 'MRK', 'PEP', 'TMO', 'ACN']

        # NASDAQ 100 top holdings
        nasdaq_leaders = ['AAPL', 'MSFT', 'AMZN', 'NVDA', 'GOOGL', 'META', 'TSLA',
                        'AVGO', 'COST', 'ADBE', 'NFLX', 'PEP', 'AMD', 'QCOM',
                        'ISRG', 'CMCSA', 'INTC', 'INTU', 'AMAT', 'BKNG']

        # Combine them (remove duplicates)
        symbols = list(set(sp500_leaders + nasdaq_leaders + etfs))
        
        # Add equities with minute resolution
        for symbol in symbols:
            self.add_equity(symbol, Resolution.MINUTE)
        
        # Store indicators per symbol
        self.window = {}
        self.price_history = {}
        
        # Initialize indicators for each symbol
        for symbol in symbols:
            sym = self.symbol(symbol)
            self.window[sym] = RollingWindow[TradeBar](2)
            self.price_history[sym] = []
        
        # Track trading signals for dynamic allocation
        self.pending_trades = {}
        
        # Schedule events for all securities
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.before_market_close("SPY", 0), 
            self.closing_bar
        )
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.after_market_open("SPY", 1), 
            self.opening_bar
        )
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.after_market_open("SPY", self.close_positions_minutes), 
            self.close_positions
        )
    
    def on_data(self, data):
        # Update volatility indicator for each symbol
        for symbol in list(self.price_history.keys()):
            if symbol in data and data[symbol] is not None:
                if self.price_history[symbol] is None:
                    self.price_history[symbol] = []
                self.price_history[symbol].append(data[symbol].close)
                if len(self.price_history[symbol]) >= self.volatility_window:
                        self.price_history[symbol] = self.price_history[symbol][-self.volatility_window:]
    
    def opening_bar(self):
        # Clear previous day's pending trades
        self.pending_trades = {}
        
        # First pass: identify all trading opportunities
        for symbol in list(self.window.keys()):
            if symbol not in self.current_slice.bars:
                continue
            
            # Add current bar to window
            self.window[symbol].add(self.current_slice[symbol])
            
            # Check if both window and volatility are ready
            if not self.window[symbol].is_ready or not len(self.price_history[symbol]) >= self.volatility_window:
                continue
            
            # Calculate gap
            delta = self.window[symbol][0].open - self.window[symbol][1].close
            
            # Calculate standard deviations
            deviations = delta / np.std(self.price_history[symbol])
            
            # Identify significant gaps (sigma+ std devs in either direction)
            if abs(deviations) >= self.sigma:
                # Store the signal: positive deviation = gap up (short), negative = gap down (long)
                # We fade the gap, so we trade opposite to the gap direction
                direction = -1 if deviations > 0 else 1  # -1 for short, 1 for long
                self.pending_trades[symbol] = {
                    'direction': direction,
                    'deviations': deviations,
                    'delta': delta
                }
                        
        # Second pass: execute trades with equal weight distribution
        if len(self.pending_trades) > 0:
            # Calculate weight per position (equal split)
            weight_per_position = 1.0 / len(self.pending_trades)
                        
            for symbol, trade_info in self.pending_trades.items():
                # Apply weight with direction (negative for shorts, positive for longs)
                position_size = weight_per_position * trade_info['direction']
                
                self.set_holdings(symbol, position_size)
                

    
    def close_positions(self):
        # Liquidate all positions
        self.liquidate()
    
    def closing_bar(self):
        # Update window with closing bar for each symbol
        for symbol in list(self.window.keys()):
            if symbol in self.current_slice.bars:
                self.window[symbol].add(self.current_slice[symbol])