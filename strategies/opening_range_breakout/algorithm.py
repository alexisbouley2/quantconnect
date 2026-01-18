# region imports
from AlgorithmImports import *
from datetime import timedelta
from typing import Optional
# endregion

class MuscularFluorescentYellowJellyfish(QCAlgorithm):
    """
    Opening Range Breakout Strategy - QuantConnect Implementation
    
    This algorithm implements a momentum breakout strategy that:
    1. Identifies the opening range (first 30 minutes) for SPY
    2. Enters long when price breaks above: or_high + (or_range * breakout_buffer)
    3. Enters short when price breaks below: or_low - (or_range * breakout_buffer)
    4. Uses a price-percentage trailing stop (Variant 2): exit on 1% reversion from high/low water mark
    5. Forces exit at 15:45 to avoid overnight risk
    
    This is the production-ready version submitted to QuantConnect platform,
    using Variant 2 (price-percentage trailing stop) based on research optimization results.
    """

    def initialize(self) -> None:
        """
        Initialize the algorithm: set dates, cash, symbols, and schedule events.
        """
        # ===== STRATEGY PARAMETERS =====
        self.opening_range_minutes: int = 30  # Duration of opening range in minutes
        self.breakout_buffer: float = 1.0  # Multiplier for breakout threshold (1.0 = full OR range)
        self.reversion_multiple: float = 0.01  # Exit threshold: 1% of price (Variant 2)
        self.exit_hour: int = 15  # Hour to force exit
        self.exit_minute: int = 45  # Minute to force exit (15:45 = 3:45 PM)
        # ================================
        
        # Backtest configuration
        self.set_start_date(2019, 1, 1)
        self.set_end_date(2023, 1, 1)
        self.set_cash(100000)
        
        # Add SPY as the trading instrument (minute resolution for intraday signals)
        self.add_equity("SPY", Resolution.MINUTE)
        
        # Consolidate bars to capture opening range (30-minute consolidated bar)
        # This consolidator will call on_data_consolidated with 30-min bars
        self.consolidate("SPY", timedelta(minutes=self.opening_range_minutes), self.on_data_consolidated)
        
        # Schedule daily exit at 15:45 (avoid overnight risk)
        self.schedule.on(
            self.date_rules.every_day("SPY"), 
            self.time_rules.at(self.exit_hour, self.exit_minute), 
            self.close_positions
        )
        
        # Track opening range and position state
        self.opening_bar: Optional[TradeBar] = None  # Consolidated bar representing opening range
        self.high_water_mark: Optional[float] = None  # Highest price since long entry
        self.low_water_mark: Optional[float] = None  # Lowest price since short entry


    def on_data(self, data: Slice) -> None:
        """
        Main strategy logic executed on every minute bar.
        
        This method handles:
        - Entry signals: breakouts above/below opening range
        - Exit signals: trailing stop based on price percentage (Variant 2)
        
        Args:
            data: Slice containing current market data
        """
        # Wait for opening range to be established
        if self.opening_bar is None:
            return

        current_price: float = data["SPY"].close
        
        # Entry logic: Check for breakout signals when not invested
        if not self.portfolio.invested:
            # Calculate opening range statistics
            or_range: float = self.opening_bar.high - self.opening_bar.low
            breakout_long: float = self.opening_bar.high + (or_range * self.breakout_buffer)
            breakout_short: float = self.opening_bar.low - (or_range * self.breakout_buffer)
            
            # Long entry: Price breaks above upper threshold
            if current_price > breakout_long:
                self.set_holdings("SPY", 1.0)  # 100% long position
                self.high_water_mark = current_price  # Initialize trailing stop

            # Short entry: Price breaks below lower threshold
            elif current_price < breakout_short:
                self.set_holdings("SPY", -1.0)  # 100% short position
                self.low_water_mark = current_price  # Initialize trailing stop
        
        # Exit logic: Trailing stop based on price percentage (Variant 2)
        else:
            position = self.portfolio["SPY"]
            is_long: bool = position.quantity > 0
            
            if is_long:
                # Update high water mark (trailing stop only moves up)
                if current_price > self.high_water_mark:
                    self.high_water_mark = current_price
                
                # Variant 2: Reversion threshold = high_water_mark * reversion_multiple (1%)
                reversion_threshold: float = self.high_water_mark * self.reversion_multiple
                reversion_level: float = self.high_water_mark - reversion_threshold
                
                # Exit if price reverts from high water mark by threshold
                if current_price < reversion_level:
                    self.close_positions()
            
            else:  # short position
                # Update low water mark (trailing stop only moves down)
                if current_price < self.low_water_mark:
                    self.low_water_mark = current_price
                
                # Variant 2: Reversion threshold = low_water_mark * reversion_multiple (1%)
                reversion_threshold = self.low_water_mark * self.reversion_multiple
                reversion_level = self.low_water_mark + reversion_threshold
                
                # Exit if price reverts from low water mark by threshold
                if current_price > reversion_level:
                    self.close_positions()
         
    def on_data_consolidated(self, bar: TradeBar) -> None:
        """
        Capture the opening range bar (first 30-minute consolidated bar).
        
        This consolidator provides a single bar representing the first 30 minutes
        of trading, which we use to define the opening range (high/low).
        
        Args:
            bar: 30-minute consolidated TradeBar
        """
        # Only capture the bar that starts at market open (9:30 AM)
        if bar.time.hour == 9 and bar.time.minute == 30:
            self.opening_bar = bar
    
    def close_positions(self) -> None:
        """
        Scheduled function to close all positions at exit time (15:45).
        
        This is called daily to ensure positions are closed before market close,
        avoiding overnight gap risk. Also resets opening_bar for next trading day.
        """
        self.liquidate("SPY")
        self.opening_bar = None  # Reset for next trading day
