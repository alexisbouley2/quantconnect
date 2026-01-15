# region imports
from AlgorithmImports import *
# endregion

# QuantBook Research Framework
import pandas as pd
import numpy as np
from datetime import datetime, time, timedelta
from typing import List, Dict, Callable, Optional, Tuple
import matplotlib.pyplot as plt
from dataclasses import dataclass

# ===== DATA CLASSES FOR CLEAN STRUCTURE =====

@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    direction: str  # 'long' or 'short'
    entry_time: datetime
    entry_price: float
    quantity: int
    metadata: Dict = None  # Store strategy-specific info (like high_water_mark)
    
@dataclass
class Trade:
    """Completed trade record"""
    symbol: str
    direction: str
    entry_time: datetime
    entry_price: float
    exit_time: datetime
    exit_price: float
    quantity: int
    pnl: float
    return_pct: float
    metadata: Dict = None

# ===== MAIN STRATEGY TESTER CLASS =====

class StrategyTester:
    """
    Framework for backtesting trading strategies on QuantConnect
    
    Usage:
        tester = StrategyTester(
            symbols=['SPY'],
            start_date=(2023, 1, 1),
            end_date=(2024, 1, 1),
            initial_cash=10000,
            resolution='minute'
        )
        
        results = tester.run(strategy_func, strategy_params)
        stats = tester.get_stats(plot=True)
    """
    
    def __init__(
        self,
        symbols: List[str],
        start_date: Tuple[int, int, int],
        end_date: Tuple[int, int, int],
        initial_cash: float = 10000,
        resolution: str = 'minute'  # 'minute', 'hour', 'daily'
    ):
        self.qb = QuantBook()
        self.symbols = symbols
        self.start_date = datetime(*start_date)
        self.end_date = datetime(*end_date)
        self.initial_cash = initial_cash
        self.resolution = resolution
        
        # Trading state
        self.cash = initial_cash
        self.positions: Dict[str, Position] = {}  # symbol -> Position
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        # Data storage
        self.data: Dict[str, pd.DataFrame] = {}  # symbol -> DataFrame
        self.current_time: datetime = None
        
        # Load data
        self._load_data()
        
    def _load_data(self):
        """Load historical data for all symbols"""
        resolution_map = {
            'minute': Resolution.MINUTE,
            'hour': Resolution.HOUR,
            'daily': Resolution.DAILY
        }
        
        for symbol_str in self.symbols:
            symbol = self.qb.add_equity(symbol_str, resolution_map[self.resolution])
            
            history = self.qb.history(
                [symbol.symbol],
                self.start_date,
                self.end_date,
                resolution_map[self.resolution]
            )
            
            # Convert to DataFrame
            df = pd.DataFrame({
                'open': history['open'].unstack(level=0)[symbol.symbol],
                'high': history['high'].unstack(level=0)[symbol.symbol],
                'low': history['low'].unstack(level=0)[symbol.symbol],
                'close': history['close'].unstack(level=0)[symbol.symbol],
            })
            
            df['date'] = df.index.date
            df['time'] = df.index.time
            
            self.data[symbol_str] = df
    
    def run(
        self,
        strategy_func: Callable,
        strategy_params: Dict = None
    ) -> 'StrategyTester':
        """
        Run backtest with given strategy function
        
        Args:
            strategy_func: Function with signature:
                def strategy(tester, current_bars, params) -> List[Order]
                where Order is a dict: {
                    'symbol': str,
                    'action': 'buy'|'sell'|'close',
                    'price': float (optional),
                    'cash_allocation': float (optional, 0.0-1.0, fraction of cash),
                    'metadata': dict (optional)
                }
            strategy_params: Dictionary of parameters to pass to strategy
            
        Returns:
            self (for method chaining)
        """
        if strategy_params is None:
            strategy_params = {}
            
        # Reset state
        self.cash = self.initial_cash
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Get all timestamps (assuming all symbols have same timestamps)
        timestamps = self.data[self.symbols[0]].index
        
        print(f"\n▶ Running backtest...")
        
        for i, timestamp in enumerate(timestamps):
            self.current_time = timestamp
            
            # Prepare current bar data for all symbols
            current_bars = {}
            for symbol in self.symbols:
                if timestamp in self.data[symbol].index:
                    current_bars[symbol] = self.data[symbol].loc[timestamp]
            
            # Call strategy function
            orders = strategy_func(self, current_bars, strategy_params)
            
            # Execute orders
            if orders:
                for order in orders:
                    self._execute_order(order)
            
            # Record equity
            equity = self._calculate_equity(current_bars)
            self.equity_curve.append((timestamp, equity))
            
            # Progress bar
            if i % 1000 == 0:
                progress = (i / len(timestamps)) * 100
                print(f"  Progress: {progress:.1f}%", end='\r')
        
        print(f"✓ Backtest complete")
        
        return self
    
    def _execute_order(self, order: Dict):
        """
        Execute a single order
        
        Required order fields:
        - 'symbol': str
        - 'action': 'buy' | 'sell' | 'close'
        - 'cash_allocation': float in [0.0, 1.0] for new positions ('buy'/'sell')
        Optional:
        - 'price': float override (otherwise current close)
        - 'metadata': dict stored on the Position
        """
        symbol = order['symbol']
        action = order['action']  # 'buy', 'sell', 'close'
        price = order.get('price')  # If None, use current market price
        metadata = order.get('metadata', {})

        current_bar = self.data[symbol].loc[self.current_time]
        if price is None:
            price = current_bar['close']


        if action == 'buy' and symbol not in self.positions:
            # Open long position       
            cash_to_use = self.cash * order['cash_allocation']  
            quantity = int(cash_to_use / price)

            if quantity > 0:
                cost = quantity * price
                self.cash -= cost
                self.positions[symbol] = Position(
                    symbol=symbol,
                    direction='long',
                    entry_time=self.current_time,
                    entry_price=price,
                    quantity=quantity,
                    metadata=metadata
                )
                
        elif action == 'sell' and symbol not in self.positions:
            # Open short position      
            cash_to_use = self.cash * order['cash_allocation']  
            quantity = int(cash_to_use / price)
                
            if quantity > 0:
                # For short positions, we need to hold cash as collateral/margin
                # Typically this is the value of the short position
                cost = quantity * price
                self.cash -= cost
                self.positions[symbol] = Position(
                    symbol=symbol,
                    direction='short',
                    entry_time=self.current_time,
                    entry_price=price,
                    quantity=quantity,
                    metadata=metadata
                )
                
        elif action == 'close' and symbol in self.positions:
            # Close position
            position = self.positions[symbol]
            
            if position.direction == 'long':
                pnl = (price - position.entry_price) * position.quantity
                return_pct = (price - position.entry_price) / position.entry_price
                # Return the original cost plus profit
                self.cash += position.entry_price * position.quantity + pnl
            else:  # short
                pnl = (position.entry_price - price) * position.quantity
                return_pct = (position.entry_price - price) / position.entry_price
                # Return the collateral plus profit
                self.cash += position.entry_price * position.quantity + pnl
            
            trade = Trade(
                symbol=symbol,
                direction=position.direction,
                entry_time=position.entry_time,
                entry_price=position.entry_price,
                exit_time=self.current_time,
                exit_price=price,
                quantity=position.quantity,
                pnl=pnl,
                return_pct=return_pct,
                metadata=position.metadata
            )
            
            self.trades.append(trade)
            del self.positions[symbol]
    
    def _calculate_equity(self, current_bars: Dict) -> float:
        """Calculate current total equity"""
        equity = self.cash
        
        for symbol, position in self.positions.items():
            if symbol in current_bars:
                current_price = current_bars[symbol]['close']
                if position.direction == 'long':
                    equity += position.quantity * current_price
                else:  # short
                    equity += position.quantity * (2 * position.entry_price - current_price)
        
        return equity
    
    def get_stats(self, plot: bool = False) -> Dict:
        """
        Calculate strategy statistics
        
        Args:
            plot: Whether to generate performance plots
            
        Returns:
            Dictionary of performance metrics
        """
        if not self.trades:
            print("⚠ No trades executed")
            return {}
        
        trades_df = pd.DataFrame([
            {
                'symbol': t.symbol,
                'direction': t.direction,
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'return': t.return_pct,
                'pnl': t.pnl
            }
            for t in self.trades
        ])
        
        # Calculate metrics
        total_return = (self.equity_curve[-1][1] - self.initial_cash) / self.initial_cash
        
        wins = trades_df[trades_df['return'] > 0]
        losses = trades_df[trades_df['return'] < 0]
        
        returns = trades_df['return']
        
        stats = {
            'total_return': total_return,
            'num_trades': len(trades_df),
            'win_rate': len(wins) / len(trades_df) if len(trades_df) > 0 else 0,
            'avg_return': returns.mean(),
            'avg_win': wins['return'].mean() if len(wins) > 0 else 0,
            'avg_loss': losses['return'].mean() if len(losses) > 0 else 0,
            'best_trade': returns.max(),
            'worst_trade': returns.min(),
            'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0,
            'profit_factor': abs(wins['pnl'].sum() / losses['pnl'].sum()) if len(losses) > 0 and losses['pnl'].sum() != 0 else np.inf,
        }
        
        # Max drawdown
        equity_series = pd.Series([eq for _, eq in self.equity_curve])
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max
        stats['max_drawdown'] = drawdown.min()
        
        # Calmar ratio
        if stats['max_drawdown'] != 0:
            stats['calmar_ratio'] = total_return / abs(stats['max_drawdown'])
        else:
            stats['calmar_ratio'] = np.inf
        
        if plot:
            self._plot_results(trades_df, stats)
        
        return stats
    
    def _plot_results(self, trades_df: pd.DataFrame, stats: Dict):
        """Generate performance plots"""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10))
        
        # Equity curve
        times, equity = zip(*self.equity_curve)
        axes[0].plot(times, equity, linewidth=2)
        axes[0].set_title(f'Equity Curve (Return: {stats["total_return"]*100:.2f}%)')
        axes[0].set_ylabel('Equity ($)')
        axes[0].grid(True, alpha=0.3)
        axes[0].axhline(y=self.initial_cash, color='gray', linestyle='--', alpha=0.5)
        
        # Drawdown
        equity_series = pd.Series(equity, index=times)
        running_max = equity_series.cummax()
        drawdown = (equity_series - running_max) / running_max * 100
        axes[1].fill_between(times, drawdown, 0, alpha=0.3, color='red')
        axes[1].plot(times, drawdown, linewidth=1, color='darkred')
        axes[1].set_title(f'Drawdown (Max: {stats["max_drawdown"]*100:.2f}%)')
        axes[1].set_ylabel('Drawdown (%)')
        axes[1].grid(True, alpha=0.3)
        
        # Return distribution
        axes[2].hist(trades_df['return'] * 100, bins=50, alpha=0.7, edgecolor='black')
        axes[2].axvline(x=0, color='red', linestyle='--', linewidth=2)
        axes[2].axvline(x=stats['avg_return'] * 100, color='green', linestyle='--', linewidth=2, 
                       label=f'Mean: {stats["avg_return"]*100:.3f}%')
        axes[2].set_title(f'Return Distribution (Win Rate: {stats["win_rate"]*100:.1f}%)')
        axes[2].set_xlabel('Return (%)')
        axes[2].set_ylabel('Frequency')
        axes[2].legend()
        axes[2].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    def print_stats(self, stats: Dict = None):
        """Pretty print statistics"""
        if stats is None:
            stats = self.get_stats(plot=False)
        
        if not stats:
            return
        
        print("\n" + "="*50)
        print("STRATEGY PERFORMANCE")
        print("="*50)
        print(f"Total Return:     {stats['total_return']*100:>8.2f}%")
        print(f"Sharpe Ratio:     {stats['sharpe_ratio']:>8.2f}")
        print(f"Max Drawdown:     {stats['max_drawdown']*100:>8.2f}%")
        print(f"Calmar Ratio:     {stats['calmar_ratio']:>8.2f}")
        print(f"\nTotal Trades:     {stats['num_trades']:>8}")
        print(f"Win Rate:         {stats['win_rate']*100:>8.1f}%")
        print(f"Profit Factor:    {stats['profit_factor']:>8.2f}")
        print(f"\nAverage Return:   {stats['avg_return']*100:>8.3f}%")
        print(f"Average Win:      {stats['avg_win']*100:>8.3f}%")
        print(f"Average Loss:     {stats['avg_loss']*100:>8.3f}%")
        print(f"Best Trade:       {stats['best_trade']*100:>8.2f}%")
        print(f"Worst Trade:      {stats['worst_trade']*100:>8.2f}%")
        print("="*50 + "\n")
    
    # Helper methods for strategy development
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get current position for symbol"""
        return self.positions.get(symbol)
    
    def has_position(self, symbol: str) -> bool:
        """Check if currently holding position in symbol"""
        return symbol in self.positions
    
    def get_open_positions_count(self) -> int:
        """Get the number of currently open positions"""
        return len(self.positions)
    
    def update_position_metadata(self, symbol: str, metadata: Dict):
        """Update metadata for open position (e.g., high_water_mark)"""
        if symbol in self.positions:
            if self.positions[symbol].metadata is None:
                self.positions[symbol].metadata = {}
            self.positions[symbol].metadata.update(metadata)
    
    def get_historical_data(self, symbol: str, lookback_bars: int = None) -> pd.DataFrame:
        """Get historical data up to current time"""
        df = self.data[symbol]
        current_idx = df.index.get_loc(self.current_time)
        
        if lookback_bars is None:
            return df.iloc[:current_idx + 1]
        else:
            start_idx = max(0, current_idx - lookback_bars + 1)
            return df.iloc[start_idx:current_idx + 1]