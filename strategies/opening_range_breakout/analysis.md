# Opening Range Breakout Strategy - Analysis

## Executive Summary

The Opening Range Breakout strategy attempts to capture momentum from price breakouts beyond the opening range (first 30 minutes) using a price-percentage trailing stop (Variant 2). While the strategy showed promising results on SPY during the optimization period (Sharpe 2.69 on 2018), it failed to generalize to other stocks (Sharpe 0.97 on multi-asset universe), revealing critical overfitting issues. The strategy demonstrates high parameter sensitivity, particularly to `breakout_buffer`. **Conclusion**: This strategy is not production-ready due to lack of robustness across assets and evidence of overfitting.

## Economic Rationale

**Hypothesis**: The market opening is highly volatile due to overnight news, late-market developments, and information accumulation. By waiting a specified period (opening range) to establish intraday volatility and price uncertainty, we can identify when a true trend signal emerges: price breaking out of the opening range indicates sustained momentum rather than noise.

**Market Microstructure Explanation**:

- Opening range (first 30 minutes) establishes intraday volatility baseline
- Breakouts beyond opening range with buffer suggest strong momentum
- Trailing stop (percentage-based) protects gains while allowing trends to run

**Behavioral Drivers**:

- **Momentum persistence**: Breakouts from opening range often continue due to institutional flow and trend-following behavior
- **Mean reversion risk**: Large gaps may revert; trailing stop mitigates this

**Strategy Logic**:

1. **Entry**: When price breaks above/below opening range + buffer threshold
   - Long: `price > or_high + (or_range * breakout_buffer)`
   - Short: `price < or_low - (or_range * breakout_buffer)`
2. **Exit**: Trailing stop based on price percentage (Variant 2)
   - Long: Exit when price reverts by `high_water_mark * reversion_multiple` (1%)
   - Short: Exit when price reverts by `low_water_mark * reversion_multiple` (1%)
3. **Time-based exit**: Force close at 15:45 to avoid overnight risk

## Methodology

### Data & Universe

- **Universe**: Initially SPY only (optimization); tested on multi-asset universe (SPY, QQQ, IWM, AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, JPM, XOM) for generalization test
- **Resolution**: Minute-level data for intraday signals
- **Data Sources**: US equity market prices via QuantConnect
- **Backtest Period**: 2018 (optimization); 2019-2023 (QuantConnect validation)

### Entry Logic

- **Opening Range**: First 30 minutes (9:30 AM - 10:00 AM)
- **Breakout Threshold**: `or_high + (or_range * breakout_buffer)` for longs, `or_low - (or_range * breakout_buffer)` for shorts
- **Buffer**: `breakout_buffer = 1.0` (full opening range distance)
- **Entry Condition**: Price must break through threshold after opening range is established

### Exit Logic

**Variant 2 (Selected)**: Price-percentage trailing stop

- **Long Positions**:
  - Track `high_water_mark` (highest price since entry)
  - Exit when: `price < high_water_mark - (high_water_mark * 0.01)`
  - Example: If high water mark = $100, exit at $99 (1% reversion)
- **Short Positions**:
  - Track `low_water_mark` (lowest price since entry)
  - Exit when: `price > low_water_mark + (low_water_mark * 0.01)`
- **Time-based Exit**: Force close all positions at 15:45 (3:45 PM) daily

**Why Variant 2 over Variant 1?**

- Variant 1 uses volatility-based trailing stop: `or_range * reversion_multiple`
- Variant 2 uses price-percentage: `high_water_mark * reversion_multiple`
- Variant 2 showed better performance in optimization (higher Sharpe, return, win rate)
- Selected for final implementation

### Position Sizing

- **Single Stock (SPY)**: 100% allocation per position
- **Multi-Asset Universe**: Equal weighting: `1 / max_positions` per position
  - `max_positions = len(universe) / 2` (half of universe size)
  - Rationale: Empirical observation that SPY was chosen 64% of days (160/250); setting to 50% provides margin for daily trading

### Parameters

Final parameters (after coordinate descent optimization):

| Parameter               | Value        | Justification                                                                                        |
| ----------------------- | ------------ | ---------------------------------------------------------------------------------------------------- |
| `opening_range_minutes` | 30           | Slightly lower Sharpe than 60/90, but much higher total return                                       |
| `breakout_buffer`       | 1.0          | Optimal from optimization; higher values (1.5, 2.0) reduce trade frequency without proportional gain |
| `reversion_multiple`    | 0.01         | 1% of price; reduces max drawdown while maintaining similar performance vs 0.03/0.05                 |
| `exit_time`             | 15:45        | Force close before market close (4:00 PM) to avoid overnight gaps                                    |
| `max_positions`         | 1 (SPY only) | Multi-asset version used `len(universe) / 2`                                                         |

**Parameter Selection Method**: Coordinate descent optimization

- Optimizes one parameter at a time using best values found so far as defaults
- Repeats until convergence or max passes reached
- Optimized for Sharpe ratio (risk-adjusted returns)

## Robustness Analysis

### Parameter Sensitivity

**Critical Finding**: `breakout_buffer` shows extreme sensitivity (major red flag)

| Parameter               | Sensitivity | Impact on Performance                                                |
| ----------------------- | ----------- | -------------------------------------------------------------------- |
| `breakout_buffer`       | **High**    | Sharpe: 1.11 (buffer=1.5) vs 2.69 (buffer=1.0) — extreme sensitivity |
| `reversion_multiple`    | Low         | Minimal impact; stable across values (0.01, 0.03, 0.05)              |
| `opening_range_minutes` | Low         | Relatively stable (30, 60, 90 all show reasonable performance)       |

**Analysis**: The extreme sensitivity of `breakout_buffer` suggests potential overfitting. A robust strategy should show more stable performance across reasonable parameter ranges.

### Crisis Period Performance

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2023)

**Overall Performance**:

- **Sharpe Ratio**: -0.4 (on multi-asset universe) — **negative, failing target of >1.5**
- **Total Return**: Negative over full period
- **Stability**: Performance is "mainly flat" across different market regimes

**Market Regimes Analysis** (from backtest report):

1. **COVID-19 Pandemic (2020)**:
   - Performance was relatively flat (didn't blow up, but didn't profit)
   - Avoided large drawdowns but failed to capture recovery rallies
2. **Post-COVID Run-up (2020-2021)**:
   - Underperformed significantly during strong bull market
   - Failed to participate in market recovery
3. **Russia Invades Ukraine (2022-2023)**:
   - Generally followed market decline without capturing recovery
4. **AI Boom / Meme Season (2021)**:
   - Underperformed during market enthusiasm

**Key Insight**: Strategy shows stability (doesn't blow up) but consistently underperforms across all regimes, suggesting it's capturing neither momentum nor mean reversion effectively in out-of-sample periods.

### Rolling Performance Stability

**Rolling Sharpe Ratio**: Varies from -2.0 to +1.0, but returns are "mainly flat"

**Analysis**: Despite varying Sharpe ratios, the underlying returns are essentially flat, suggesting the strategy lacks consistent edge. The rolling metrics show volatility in risk-adjusted returns but no sustained positive performance.

### Generalization Test: Single Stock vs Multi-Asset Universe

**Test Design**:

- **SPY Only** (2018): Sharpe 2.69, Total Return 16.13%
- **Multi-Asset** (12 stocks: SPY, QQQ, IWM, AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, JPM, XOM): Sharpe 0.97, Total Return 3.97%

**Critical Failure**:

- **Observation**: Performance degraded significantly when expanding universe (Sharpe: 2.69 → 0.97)
- **Expected**: If strategy captures real market phenomena, it should generalize across stocks
- **Reality**: Sharp performance drop indicates strategy is **not generalizing**
- **Root Cause**: Likely overfitting to SPY-specific characteristics (liquidity patterns, volatility structure, etc.)

**Additional Red Flags**:

- Returns are "mainly flat" with only a few large jumps (low statistical reliability)
- Strategy optimized on SPY fails on other stocks, indicating overfitting

## Risk Analysis

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2023 on SPY)

### Risk Metrics

| Metric                     | Value       | Interpretation                                                                                    |
| -------------------------- | ----------- | ------------------------------------------------------------------------------------------------- |
| **Maximum Drawdown**       | 16.5%       | Cumulative loss during 2019-2021 period; explained by flat returns and constant transaction costs |
| **Worst Single-Day Loss**  | < -1%       | Reasonable given trailing stop mechanism limits daily exposure                                    |
| **Correlation to SPY**     | -0.03       | Slightly negative, close to zero — suggests market-neutral characteristics (as intended)          |
| **Position Concentration** | 100% on SPY | Single-asset concentration (in final validation)                                                  |
| **Maximum Leverage**       | 1.0         | No leverage; 100% long or short only                                                              |
| **Turnover**               | Moderate    | Daily trading with time-based exits                                                               |

### Risk Controls

Current risk controls implemented in algorithm:

1. **Time-based Exit (15:45)**: Prevents overnight gap risk by closing positions before market close
2. **Trailing Stop (1%)**: Protects gains and limits losses via price-percentage stop
3. **Position Size Limit**: Single position (100% allocation) or `max_positions` limit for multi-asset
4. **No Re-entry on Same Day**: Prevents overtrading; one trade per symbol per day

**Missing Risk Controls** (for production):

- Maximum portfolio drawdown circuit breaker
- Daily loss limits
- Correlation limits (for multi-asset versions)
- Volatility-based position sizing

## Performance Attribution

### What Drives Returns

**Entry Timing vs Exit Timing**:

- **Entry**: Breakout signals are relatively infrequent (depends on `breakout_buffer` threshold)
- **Exit**: Trailing stop exits are more frequent; time-based exits ensure daily closure
- **Contribution**: Difficult to isolate, but flat returns suggest neither entry nor exit is generating consistent edge

**Market Selection vs Individual Stock Selection**:

- **Strategy Design**: Single stock (SPY) in final version
- **Selection Rationale**: Multi-asset testing showed poor generalization; focused on SPY-only version
- **Reality**: Even SPY-only version underperforms in out-of-sample (2019-2023)

**Concentration Effects**:

- **Observation**: Returns are "well spread across time" (not concentrated in a few days)
- **Analysis**: Good from diversification perspective, but suggests strategy lacks strong directional bias
- **Trade-off**: Diffuse returns may indicate weak signal strength

**Return Distribution**:

- **Pattern**: Returns are "mainly flat" with only occasional large jumps
- **Implication**: Strategy relies on rare, large-magnitude events rather than consistent edge
- **Risk**: Low statistical reliability; high variance in outcomes

## Limitations & Future Work

### Known Weaknesses

1. **Lack of Robustness**:

   - Strategy fails to generalize beyond SPY (Sharpe: 2.69 → 0.97)
   - High parameter sensitivity (`breakout_buffer` extreme sensitivity)
   - Evidence of overfitting to training period

2. **Poor Out-of-Sample Performance**:

   - Negative Sharpe ratio (-0.4) on validation period (2019-2023)
   - Consistent underperformance across all market regimes
   - Returns are flat rather than positive

3. **Statistical Reliability**:

   - Returns depend on rare, large-magnitude events
   - Low consistency across time periods
   - High variance in outcomes

4. **Parameter Sensitivity**:
   - Extreme sensitivity to `breakout_buffer` (red flag for generalization)
   - Suggests strategy may not be capturing robust market phenomena

### What Would Be Needed for Production-Ready

**This strategy is currently not usable** due to:

- Lack of robustness across assets
- Poor out-of-sample performance
- Evidence of overfitting

**Improvements Required**:

1. **Parameter Robustness**:

   - Reduce sensitivity to `breakout_buffer` (investigate why it's so critical)
   - Consider regime-dependent parameters (different thresholds for different volatility regimes)
   - Test walk-forward optimization instead of single-period optimization

2. **Generalization**:

   - Investigate why strategy fails on other stocks (SPY-specific patterns?)
   - Consider asset-specific parameter adaptation
   - Test on completely different time periods (different decades)

3. **Signal Quality**:

   - Explore additional filters to improve signal reliability
   - Consider combining with other signals (momentum, mean reversion, volume)
   - Investigate why returns are "flat" — is the signal too weak?

4. **Risk Management**:
   - Add portfolio-level risk controls (max drawdown, daily loss limits)
   - Implement volatility-based position sizing
   - Consider dynamic hedging or correlation limits

### Key Learnings

**What Worked**:

- Time-based exits prevent overnight risk (good risk control)
- Trailing stop mechanism functions as intended (exits on reversion)
- Strategy shows stability (doesn't blow up in crises)

**What Didn't Work**:

- Strategy fails to generalize beyond single stock
- Optimization process led to overfitting
- Returns are flat rather than positive
- Parameter sensitivity reveals lack of robustness

**Critical Insight**: A strategy that performs well on a single stock during optimization but fails on other stocks is likely capturing stock-specific patterns rather than universal market phenomena. This is a common pitfall in quantitative strategy development and highlights the importance of robustness testing early in the research process.
