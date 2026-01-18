# region imports
from AlgorithmImports import *
from typing import Dict, Optional
# endregion

import numpy as np

class FadingTheGap(QCAlgorithm):
    """
    Overnight Gap Mean Reversion Strategy - QuantConnect Implementation
    
    This algorithm implements a mean reversion strategy that:
    1. Identifies unusual overnight gaps (price jumps from previous day's close to today's open)
    2. Filters gaps using volatility: abs(gap) >= sigma * volatility (rolling std dev)
    3. Enters positions at 9:31 AM (1 minute after market open)
       - Upward gaps → Short positions (bet on reversion down)
       - Downward gaps → Long positions (bet on reversion up)
    4. Exits all positions at market open + close_positions_minutes (e.g., 9:45 AM)
    
    This is the production-ready version submitted to QuantConnect platform,
    optimized for multi-asset universe (major ETFs and liquid stocks).
    """

    def initialize(self) -> None:
        """
        Initialize the algorithm: set dates, cash, symbols, and schedule events.
        """
        # ===== STRATEGY PARAMETERS =====
        self.sigma: float = 10.0  # Multiplier for gap threshold (higher = fewer but stronger signals)
        self.close_positions_minutes: int = 15  # Minutes after market open to exit (9:45 AM)
        self.volatility_window: int = 60  # Rolling window size for volatility calculation
        # ================================
        
        # Backtest configuration
        self.set_start_date(2018, 1, 1)
        self.set_end_date(2019, 1, 1)
        self.set_cash(100000)
        
        # Define diversified universe: Major indices + high-liquidity stocks across sectors
        # Indices: SPY (S&P 500), QQQ (NASDAQ), IWM (Russell 2000), DIA (Dow Jones)
        # Tech: AAPL, MSFT, GOOGL, AMZN, NVDA, META, TSLA
        # Finance: JPM, BAC, V, MA
        # Healthcare: JNJ, UNH, ABBV, MRK
        # Consumer: WMT, HD, PG, PEP, COST, DIS
        # Energy: XOM, CVX
        # Industrials: ACN, TMO
        
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
        
        # Add equities with minute resolution (required for intraday signals)
        for symbol in symbols:
            self.add_equity(symbol, Resolution.MINUTE)
        
        # Store indicators per symbol
        self.window: Dict[Symbol, RollingWindow[TradeBar]] = {}  # Rolling window for gap calculation
        self.price_history: Dict[Symbol, list] = {}  # Price history for volatility calculation
        
        # Initialize indicators for each symbol
        for symbol in symbols:
            sym: Symbol = self.symbol(symbol)
            self.window[sym] = RollingWindow[TradeBar](2)  # Need 2 bars: yesterday's close, today's open
            self.price_history[sym] = []  # Will store close prices for volatility
        
        # Track trading signals for dynamic allocation (identified in opening_bar, executed in on_data)
        self.pending_trades: Dict[Symbol, Dict[str, Any]] = {}
        
        # Schedule events for all securities
        # Update closing bar before market close (capture previous day's close)
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.before_market_close("SPY", 0), 
            self.closing_bar
        )
        # Identify and enter trades at 9:31 AM (1 minute after market open)
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.after_market_open("SPY", 1), 
            self.opening_bar
        )
        # Exit all positions at specified time after market open (e.g., 9:45 AM)
        self.schedule.on(
            self.date_rules.every_day(), 
            self.time_rules.after_market_open("SPY", self.close_positions_minutes), 
            self.close_positions
        )
    
    def on_data(self, data: Slice) -> None:
        """
        Update volatility indicator for each symbol using rolling price history.
        
        This method maintains a rolling window of close prices for each symbol,
        which is used to calculate volatility for gap filtering.
        
        Args:
            data: Slice containing current market data
        """
        # Update price history for volatility calculation (maintain rolling window)
        for symbol in list(self.price_history.keys()):
            if symbol in data and data[symbol] is not None:
                # Initialize if needed
                if self.price_history[symbol] is None:
                    self.price_history[symbol] = []
                
                # Append current close price
                self.price_history[symbol].append(data[symbol].close)
                
                # Maintain rolling window: keep only last volatility_window prices
                if len(self.price_history[symbol]) >= self.volatility_window:
                    self.price_history[symbol] = self.price_history[symbol][-self.volatility_window:]
    
    def opening_bar(self) -> None:
        """
        Identify trading opportunities at market open and execute positions.
        
        This method:
        1. Calculates overnight gaps for all symbols
        2. Filters gaps using volatility threshold (sigma * volatility)
        3. Identifies qualifying symbols for mean reversion trades
        4. Executes equal-weighted positions across all qualifying symbols
        """
        # Clear previous day's pending trades
        self.pending_trades = {}
        
        # First pass: Identify all trading opportunities
        for symbol in list(self.window.keys()):
            if symbol not in self.current_slice.bars:
                continue
            
            # Add current bar to window (today's open bar)
            self.window[symbol].add(self.current_slice[symbol])
            
            # Check if both window and volatility are ready (need sufficient data)
            if not self.window[symbol].is_ready or not len(self.price_history[symbol]) >= self.volatility_window:
                continue
            
            # Calculate gap: today's open - yesterday's close
            delta: float = self.window[symbol][0].open - self.window[symbol][1].close
            
            # Calculate volatility: rolling standard deviation of close prices
            volatility: float = np.std(self.price_history[symbol])
            
            # Skip if volatility is invalid
            if volatility is None or volatility <= 0:
                continue
            
            # Calculate gap in standard deviations
            deviations: float = delta / volatility
            
            # Identify significant gaps: abs(deviations) >= sigma
            # This filters for gaps that are statistically unusual (sigma standard deviations)
            if abs(deviations) >= self.sigma:
                # Store the signal: positive deviation = gap up (short), negative = gap down (long)
                # We fade the gap (mean reversion), so we trade opposite to the gap direction
                direction: int = -1 if deviations > 0 else 1  # -1 for short, 1 for long
                self.pending_trades[symbol] = {
                    'direction': direction,
                    'deviations': deviations,
                    'delta': delta
                }
                        
        # Second pass: Execute trades with equal weight distribution
        if len(self.pending_trades) > 0:
            # Calculate weight per position (equal split across all qualifying symbols)
            weight_per_position: float = 1.0 / len(self.pending_trades)
                        
            # Enter positions for all qualifying symbols
            for symbol, trade_info in self.pending_trades.items():
                # Apply weight with direction (negative for shorts, positive for longs)
                position_size: float = weight_per_position * trade_info['direction']
                
                self.set_holdings(symbol, position_size)
                

    
    def close_positions(self) -> None:
        """
        Scheduled function to close all positions at exit time.
        
        This is called daily at market open + close_positions_minutes (e.g., 9:45 AM)
        to limit intraday exposure and prevent holding positions too long.
        """
        self.liquidate()
    
    def closing_bar(self) -> None:
        """
        Update window with closing bar for each symbol at market close.
        
        This captures the previous day's close price, which is needed to calculate
        the overnight gap at the next market open.
        """
        # Update window with closing bar for each symbol (capture yesterday's close)
        for symbol in list(self.window.keys()):
            if symbol in self.current_slice.bars:
                self.window[symbol].add(self.current_slice[symbol])