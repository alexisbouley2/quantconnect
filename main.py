# region imports
from AlgorithmImports import *
from datetime import timedelta
# endregion

class MuscularFluorescentYellowJellyfish(QCAlgorithm):

    def initialize(self):
        # ===== PARAMETERS =====
        self.opening_range_minutes = 30
        self.breakout_buffer = 1
        self.reversion_multiple = 0.01  # 1% of price (variant 2)
        self.exit_hour = 15
        self.exit_minute = 45
        # ======================
        
        self.set_start_date(2019, 1, 1)
        self.set_end_date(2023, 1, 1)
        self.set_cash(100000)
        
        self.add_equity("SPY", Resolution.MINUTE)
        self.consolidate("SPY", timedelta(minutes=self.opening_range_minutes), self.on_data_consolidated)
        
        # Schedule exit time check
        self.schedule.on(self.date_rules.every_day("SPY"), 
                        self.time_rules.at(self.exit_hour, self.exit_minute), 
                        self.close_positions)
        
        # Track opening range and position state
        self.opening_bar = None
        self.high_water_mark = None
        self.low_water_mark = None


    def on_data(self, data):
        """Main strategy logic"""

        if self.opening_bar is None:
            return

        current_price = data["SPY"].close
        # Entry logic
        if not self.portfolio.invested:
            or_range = self.opening_bar.high - self.opening_bar.low
            breakout_long = self.opening_bar.high + (or_range * self.breakout_buffer)
            breakout_short = self.opening_bar.low - (or_range * self.breakout_buffer)
            
            if current_price > breakout_long:
                # Enter long
                self.set_holdings("SPY", 1.0)
                self.high_water_mark = current_price

            elif current_price < breakout_short:
                # Enter short
                self.set_holdings("SPY", -1.0)
                self.low_water_mark = current_price
        
        # Exit logic (reversion check)
        else:
            position = self.portfolio["SPY"]
            is_long = position.quantity > 0
            
            if is_long:
                # Update high water mark
                if current_price > self.high_water_mark:
                    self.high_water_mark = current_price
                
                # Variant 2: Reversion threshold based on price percentage
                reversion_threshold = self.high_water_mark * self.reversion_multiple
                reversion_level = self.high_water_mark - reversion_threshold
                
                # Check reversion
                if current_price < reversion_level:
                    self.close_positions()
            else:  # short
                # Update low water mark
                if current_price < self.low_water_mark:
                    self.low_water_mark = current_price
                
                # Variant 2: Reversion threshold based on price percentage
                reversion_threshold = self.low_water_mark * self.reversion_multiple
                reversion_level = self.low_water_mark + reversion_threshold
                
                # Check reversion
                if current_price > reversion_level:
                    self.close_positions()
         
    def on_data_consolidated(self, bar):
        """Capture the opening range bar (9:30 bar)"""
        if bar.time.hour == 9 and bar.time.minute == 30:
            self.opening_bar = bar
    
    def close_positions(self):
        """Scheduled function to close positions at exit time"""
        self.liquidate("SPY")
        self.opening_bar = None
