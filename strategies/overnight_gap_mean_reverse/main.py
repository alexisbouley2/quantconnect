# region imports
from AlgorithmImports import *
# endregion
class FadingTheGap(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2017, 11, 1)
        self.set_end_date(2018, 7, 1)
        self.set_cash(100000) 
        self.add_equity("TSLA", Resolution.MINUTE)
        
        self.schedule.on(self.date_rules.every_day(), self.time_rules.before_market_close("TSLA", 0), self.closing_bar) 
        self.schedule.on(self.date_rules.every_day(), self.time_rules.after_market_open("TSLA", 1), self.opening_bar)
        self.schedule.on(self.date_rules.every_day(), self.time_rules.after_market_open("TSLA", 45), self.close_positions) 
        
        self.window = RollingWindow[TradeBar](2)
                
        #1. Create a manual Standard Deviation indicator to track recent volatility
        self.volatility = StandardDeviation("TSLA", 60)
        
    def on_data(self, data):
        if data["TSLA"] is not None: 
            #2. Update our standard deviation indicator manually with algorithm time and TSLA's close price
            self.volatility.update(self.time, data["TSLA"].close)
    
    def opening_bar(self):
        if "TSLA" in self.current_slice.bars:
            self.window.add(self.current_slice["TSLA"])
        
        #3. Use is_ready to check if both volatility and the window are ready, if not ready 'return'
        if not self.window.is_ready or not self.volatility.is_ready:
            return
        
        delta = self.window[0].open - self.window[1].close
        
        #4. Save an approximation of standard deviations to our deviations variable by dividing delta by the current volatility value:
        #   Normally this is delta from the mean, but we'll approximate it with current value for this lesson. 
        deviations = delta / self.volatility.current.value

        print('delta: ', delta)
        print('self.volatility.current.value: ', self.volatility.current.value)
        
        #5. set_holdings to 100% TSLA if deviations is less than -3 standard deviations from the mean:
        if deviations < -3:
            self.set_holdings("TSLA", 1)
        
    def close_positions(self):
        self.liquidate()
        
    def closing_bar(self):
        self.window.add(self.current_slice["TSLA"])
        
