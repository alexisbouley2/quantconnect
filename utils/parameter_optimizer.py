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
    metric: str = 'sharpe_ratio',
    max_passes: int = 10
) -> pd.DataFrame:
    """
    Run coordinate descent optimization over parameter space
    
    Optimizes one parameter at a time, using best values found so far as defaults
    for subsequent parameters. Repeats until convergence or max_passes reached.
    
    Args:
        tester_config: Config for StrategyTester
        strategy_func: Strategy function to test
        param_grid: Dictionary of parameter names to lists of values to test
        metric: Metric to optimize ('sharpe_ratio', 'total_return', etc.)
        max_passes: Maximum number of optimization passes (default: 10)
        
    Returns:
        DataFrame with all results sorted by metric
    """
    param_names = list(param_grid.keys())
    
    # Extract default values (middle value of each parameter list)
    def get_default_value(values):
        """Get middle value from list"""
        # For time strings (HH:MM format), convert to minutes for sorting
        if isinstance(values[0], str) and ':' in str(values[0]):
            def time_to_minutes(time_str):
                hour, minute = map(int, str(time_str).split(':'))
                return hour * 60 + minute
            sorted_vals = sorted(values, key=time_to_minutes)
        else:
            sorted_vals = sorted(values) if not isinstance(values[0], str) else values
        mid_idx = len(sorted_vals) // 2
        return sorted_vals[mid_idx]
    
    defaults = {name: get_default_value(param_grid[name]) for name in param_names}
    
    print(f"\n▶ Coordinate Descent Optimization")
    print(f"   Optimizing for: {metric}")
    print(f"   Parameters: {', '.join(param_names)}")
    print(f"   Initial defaults: {defaults}")
    
    all_results = []
    current_best = defaults.copy()
    pass_num = 0
    
    # Cache to avoid re-running same parameter combinations
    cache = {}  # key: tuple of sorted (param_name, param_value) pairs, value: stats dict
    
    def get_cache_key(params):
        """Create hashable cache key from params dict"""
        # Convert to tuple of (name, value) pairs, ensuring values are hashable
        items = []
        for key, value in sorted(params.items()):
            # Convert numpy types to Python types for hashing
            if hasattr(value, 'item'):  # numpy scalar
                value = value.item()
            items.append((key, value))
        return tuple(items)
    
    while pass_num < max_passes:
        pass_num += 1
        print(f"\n--- Pass {pass_num} ---")
        previous_best = current_best.copy()
        
        # Optimize each parameter in sequence
        for param_name in param_names:
            print(f"  Optimizing {param_name}... \n", end=' ')
            
            # Test all values for this parameter, keeping others at current best
            param_results = []
            
            for param_value in param_grid[param_name]:
                # Create params dict with current best values, but override this parameter
                test_params = current_best.copy()
                test_params[param_name] = param_value
                
                # Check cache first
                cache_key = get_cache_key(test_params)
                was_cached = cache_key in cache
                
                if was_cached:
                    # Use cached result
                    stats = cache[cache_key]
                else:
                    # Run backtest
                    tester = StrategyTester(**tester_config)
                    tester.run(strategy_func, test_params)
                    stats = tester.get_stats(plot=False)
                    # Cache the result
                    if stats:
                        cache[cache_key] = stats
                
                if stats:
                    result = {**test_params, **stats}
                    param_results.append(result)
                    # Only append to all_results if it wasn't cached (avoid duplicates)
                    if not was_cached:
                        all_results.append(result)
            
            # Find best value for this parameter
            if param_results:
                param_df = pd.DataFrame(param_results)
                best_row = param_df.loc[param_df[metric].idxmax()]
                best_value = best_row[param_name]
                best_metric = best_row[metric]
                
                current_best[param_name] = best_value
                print(f"\nbest = {best_value} ({metric} = {best_metric:.4f})\n")
            else:
                print("no valid results")
        
        # Check for convergence
        if current_best == previous_best:
            print(f"\n✓ Converged after {pass_num} passes")
            print(f"   Final parameters: {current_best}")
            break
        
        print(f"   Updated: {current_best}")
    
    if pass_num >= max_passes:
        print(f"\n⚠ Reached max passes ({max_passes})")
        print(f"   Final parameters: {current_best}")
    
    # Return all results sorted by metric
    results_df = pd.DataFrame(all_results)
    if not results_df.empty:
        results_df = results_df.sort_values(metric, ascending=False)
        total_tests = len(all_results)
        unique_combinations = len(cache)
        print(f"\n✓ Optimization complete ({total_tests} total tests, {unique_combinations} unique combinations)")
    
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
# from parameter_optimizer import optimize_parameters, plot_parameter_sensitivity
# from strategies.opening_range_breakout.variant_1 import opening_range_breakout as variant_1_strategy
# from strategies.opening_range_breakout.variant_2 import opening_range_breakout as variant_2_strategy


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
#     'max_positions': [1, 3, 5],
#     'exit_time': ['15:00', '15:30', '15:45']
# }

# results = optimize_parameters(
#     tester_config,
#     variant_1_strategy,
#     param_grid,
#     metric='sharpe_ratio'
# )

# # View top 10 results
# print("\nTop 10 Parameter Combinations:")
# results[['opening_range_minutes', 'breakout_buffer', 'reversion_multiple', 
#                'max_positions', 'exit_time',
#                'sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate']].head(10)



# plot_parameter_sensitivity(results, 'opening_range_minutes', 'sharpe_ratio')