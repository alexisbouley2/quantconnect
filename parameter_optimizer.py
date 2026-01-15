# region imports
from AlgorithmImports import *
# endregion

# QuantBook Research Framework
import pandas as pd
import numpy as np
from typing import List, Dict, Callable, Optional, Tuple
from tester import StrategyTester
import matplotlib.pyplot as plt


# ===== PARAMETER OPTIMIZATION FRAMEWORK =====

def optimize_parameters(
    tester_config: Dict,
    strategy_func: Callable,
    param_grid: Dict[str, List],
    metric: str = 'sharpe_ratio'
) -> pd.DataFrame:
    """
    Run grid search over parameter space
    
    Args:
        tester_config: Config for StrategyTester
        strategy_func: Strategy function to test
        param_grid: Dictionary of parameter names to lists of values
        metric: Metric to optimize ('sharpe_ratio', 'total_return', etc.)
        
    Returns:
        DataFrame with all results sorted by metric
    """
    from itertools import product
    
    # Generate all parameter combinations
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    print(f"\nTesting {len(combinations)} parameter combinations...")
    print(f"   Optimizing for: {metric}")
    
    results = []
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        
        # Run backtest
        tester = StrategyTester(**tester_config)
        tester.run(strategy_func, params)
        stats = tester.get_stats(plot=False)
        
        if stats:
            result = {**params, **stats}
            results.append(result)
        
        # Progress
        if (i + 1) % 10 == 0:
            print(f"   Progress: {i+1}/{len(combinations)}")
    
    results_df = pd.DataFrame(results)
    results_df = results_df.sort_values(metric, ascending=False)
    
    print(f"✓ Optimization complete")
    return results_df


# Plot parameter sensitivity
def plot_parameter_sensitivity(results_df, param_name, metric='sharpe_ratio'):
    """
    Plot how metric varies with parameter using a line plot
    
    Handles:
    - Numerical parameters: plots as continuous line
    - Time parameters (HH:MM format): converts to minutes and plots chronologically
    - Date parameters: plots chronologically
    
    Args:
        results_df: DataFrame with optimization results
        param_name: Name of parameter to analyze
        metric: Metric to plot (default: 'sharpe_ratio')
    """
    from datetime import datetime, time
    
    plt.figure(figsize=(10, 6))
    
    # Group by parameter value and calculate mean metric
    grouped = results_df.groupby(param_name)[metric].agg(['mean', 'std', 'min', 'max'])
    
    # Determine parameter type and prepare x-axis values
    sample_value = results_df[param_name].iloc[0]
    
    if pd.api.types.is_numeric_dtype(results_df[param_name]):
        # Numerical parameter - sort numerically
        grouped = grouped.sort_index()
        x_values = grouped.index.values
        x_labels = x_values
        xlabel = param_name
        
    elif isinstance(sample_value, str) and ':' in str(sample_value):
        # Time parameter (e.g., '15:30') - convert to minutes since midnight for ordering
        def time_to_minutes(time_str):
            """Convert 'HH:MM' to minutes since midnight"""
            hour, minute = map(int, str(time_str).split(':'))
            return hour * 60 + minute
        
        # Create a mapping of time string to minutes for sorting
        time_mapping = {val: time_to_minutes(val) for val in grouped.index}
        # Sort by minutes value
        sorted_times = sorted(grouped.index, key=lambda x: time_mapping.get(x, 0))
        grouped = grouped.reindex(sorted_times)
        x_values = [time_mapping.get(val, 0) for val in grouped.index]
        x_labels = grouped.index.values  # Keep original labels for display
        xlabel = param_name
        
    elif pd.api.types.is_datetime64_any_dtype(results_df[param_name]):
        # Date parameter - sort chronologically
        grouped = grouped.sort_index()
        x_values = grouped.index.values
        x_labels = x_values
        xlabel = param_name
        
    else:
        # Categorical/other - use as-is
        x_values = range(len(grouped.index))
        x_labels = grouped.index.values
        xlabel = param_name
    
    # Plot mean line
    plt.plot(x_values, grouped['mean'], marker='o', linewidth=2, markersize=8, 
             label='Mean', color='blue')
    
    # Add error bars showing std deviation
    if grouped['std'].notna().any():
        plt.errorbar(x_values, grouped['mean'], yerr=grouped['std'], 
                    fmt='none', alpha=0.3, color='blue', capsize=5)
    
    # Add shaded region showing min-max range
    plt.fill_between(x_values, grouped['min'], grouped['max'], 
                     alpha=0.2, color='blue', label='Min-Max Range')
    
    # Set x-axis labels
    if isinstance(sample_value, str) and ':' in str(sample_value):
        # For time parameters, show original time strings
        plt.xticks(x_values, x_labels, rotation=45, ha='right')
    else:
        plt.xticks(x_values, x_labels, rotation=45, ha='right')
    
    plt.xlabel(xlabel)
    plt.ylabel(metric)
    plt.title(f'{metric} vs {param_name}')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()


# ===== USAGE: PARAMETER OPTIMIZATION =====
#from parameter_optimizer import optimize_parameters, plot_parameter_sensitivity
#from strategies.opening_range_breakout_strategy import opening_range_breakout_strategy

# tester_config = {
#     'symbols': ['SPY'],
#     'start_date': (2023, 1, 1),
#     'end_date': (2024, 1, 1),
#     'initial_cash': 10000,
#     'resolution': 'minute'
# }

# param_grid = {
#     'opening_range_minutes': [15, 30, 60],
#     'breakout_buffer': [0, 0.2, 0.4],
#     'reversion_multiple': [0.3, 0.5, 0.75],
#     'cash_allocation': [0.5, 0.75, 0.95],
#     'exit_time': ['15:00', '15:30', '15:45']
# }

# results = optimize_parameters(
#     tester_config,
#     opening_range_breakout_strategy,
#     param_grid,
#     metric='sharpe_ratio'
# )

# # View top 10 results
# print("\nTop 10 Parameter Combinations:")
# print(results[['opening_range_minutes', 'breakout_buffer', 'reversion_multiple', 
#                'cash_allocation', 'exit_time',
#                'sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate']].head(10))



# plot_parameter_sensitivity(results, 'opening_range_minutes', 'sharpe_ratio')