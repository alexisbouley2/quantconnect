# region imports
from AlgorithmImports import *
# endregion


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


# ===== USAGE: PARAMETER OPTIMIZATION =====

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
#     'reversion_multiple': [0.3, 0.5, 0.75]
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
#                'sharpe_ratio', 'total_return', 'max_drawdown', 'win_rate']].head(10))

# # Plot parameter sensitivity
# def plot_parameter_sensitivity(results_df, param_name, metric='sharpe_ratio'):
#     """Plot how metric varies with parameter"""
#     plt.figure(figsize=(10, 6))
    
#     for val in results_df[param_name].unique():
#         subset = results_df[results_df[param_name] == val]
#         plt.scatter([val] * len(subset), subset[metric], alpha=0.6, s=50)
    
#     plt.xlabel(param_name)
#     plt.ylabel(metric)
#     plt.title(f'{metric} vs {param_name}')
#     plt.grid(True, alpha=0.3)
#     plt.show()

# plot_parameter_sensitivity(results, 'opening_range_minutes', 'sharpe_ratio')