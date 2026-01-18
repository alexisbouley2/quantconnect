# Overnight Gap Mean Reversion Strategy - Analysis

## Executive Summary

The Overnight Gap Mean Reversion strategy attempts to profit from mean reversion of unusual overnight price gaps. The hypothesis is that large gaps (caused by after-hours news, wider spreads, or emergency trading) tend to revert during regular market hours. While the strategy showed promising in-sample results during optimization (Sharpe 6.06 on SPY, 2018), it failed catastrophically in out-of-sample validation (Sharpe -2.2, 2019-2023). The strategy's returns are driven by rare, large-magnitude events rather than consistent edge, and it fails to survive transaction costs. **Conclusion**: This strategy is not production-ready. The poor performance appears to be largely driven by bid-ask spread costs at market open, which overwhelm any mean reversion edge.

## Economic Rationale

**Hypothesis**: Overnight unexpected gaps may be due to:

- **Post-market trading**: Larger bid-ask spreads in after-hours trading
- **Emergency needs**: Urgent trading by institutional agents outside regular hours
- **Information asymmetry**: Overnight news that hasn't been fully processed

We bet on the fact that these gaps should strongly mean-revert during the opening market as normal liquidity returns and spreads narrow.

**Market Microstructure Explanation**:

- **Bid-ask spreads**: Wider spreads in after-hours markets can cause gaps that don't reflect true price movement
- **Liquidity return**: Normal market liquidity at 9:30 AM should cause price to revert toward previous day's close
- **Gap persistence risk**: Large gaps may persist if they reflect true fundamental information; volatility-based filtering attempts to identify statistical outliers

**Behavioral Drivers**:

- **Mean reversion**: Extreme overnight moves often overreact to news and revert during regular trading
- **Market efficiency**: Large gaps without fundamental justification should correct as market opens
- **Liquidity effects**: After-hours thin liquidity can cause temporary price distortions

**Strategy Logic**:

1. **Gap Calculation**: `gap = Price(d).open - Price(d-1).close`
2. **Volatility Estimation**: `volatility = std(rolling_window(n)(Price))`
3. **Signal Identification**: Bet on mean reversion when `abs(gap) >= volatility * sigma`
4. **Entry**: At 9:31 AM (1 minute after market open)
   - Upward gaps → Short positions (bet on reversion down)
   - Downward gaps → Long positions (bet on reversion up)
5. **Exit**: At market open + exit_minutes (e.g., 9:45 AM)

## Methodology

### Data & Universe

- **Universe**: Initially SPY only (optimization); expanded to multi-asset universes (12 stocks, then ~45 assets) for generalization tests
- **Resolution**: Minute-level data for intraday signals
- **Data Sources**: US equity market prices via QuantConnect
- **Backtest Period**: 2018 (optimization/in-sample); 2019-2023 (out-of-sample validation)

### Entry Logic

**Gap Calculation**:

- **Gap**: `Price(d).open - Price(d-1).close` (overnight price jump)
- **Volatility**: Rolling standard deviation of close prices: `std(rolling_window(n)(Price))`
- **Threshold**: `abs(gap) >= volatility * sigma` (where sigma = 10 standard deviations)

**Entry Conditions**:

- Gap must exceed volatility threshold (unusual gap)
- Entry at 9:31 AM (1 minute after market open, allowing market to open)
- Direction: Fade the gap (bet opposite to gap direction)

### Exit Logic

**Time-based Exit**: Force close all positions at market open + `exit_minutes_after_open` (15 minutes = 9:45 AM)

**Rationale**:

- Limits intraday exposure
- Exits before mid-day when mean reversion effect should have played out
- Avoids holding positions too long if gap doesn't revert

### Position Sizing

- **Multi-Asset Universe**: Equal weighting across all qualifying symbols
  - `cash_allocation = 1.0 / num_qualifying_symbols`
  - All qualifying symbols get equal allocation on entry day
- **Dynamic Allocation**: Number of positions varies daily based on how many symbols have unusual gaps

### Parameters

Final parameters (after coordinate descent optimization):

| Parameter                 | Value | Justification                                                                                    |
| ------------------------- | ----- | ------------------------------------------------------------------------------------------------ |
| `volatility_window`       | 60    | Rolling window size for volatility calculation; relatively stable across values (15-90)          |
| `sigma`                   | 10.0  | Gap threshold multiplier; higher values = fewer but stronger signals (optimal from optimization) |
| `exit_minutes_after_open` | 15    | Minutes after market open to exit; minimal exposure time while maintaining performance           |

**Parameter Selection Method**: Coordinate descent optimization

- Optimizes one parameter at a time using best values found so far as defaults
- Repeats until convergence or max passes reached
- Optimized for Sharpe ratio (risk-adjusted returns)

**Parameter Sensitivity**:

- **`volatility_window`**: Low sensitivity; stable performance across values (15-90)
- **`sigma`**: High sensitivity; higher sigma improves win rate but reduces trade frequency dramatically
  - With sigma > 5, less than 10 events per year for single asset (very low frequency)
- **`exit_minutes_after_open`**: Low sensitivity; doesn't significantly impact performance

## Robustness Analysis

### Parameter Sensitivity

**Key Finding**: `sigma` is the critical parameter; `volatility_window` and `exit_minutes_after_open` are relatively stable

| Parameter                 | Sensitivity | Impact on Performance                                      |
| ------------------------- | ----------- | ---------------------------------------------------------- |
| `volatility_window`       | Low         | Minimal impact; stable across values (15-90)               |
| `sigma`                   | **High**    | Higher sigma = fewer trades but better win rate; trade-off |
| `exit_minutes_after_open` | Low         | Minimal impact; doesn't significantly affect performance   |

**Analysis**: The strategy shows good robustness to `volatility_window` and `exit_minutes_after_open`, but high sensitivity to `sigma`. However, the extreme sigma value (10.0) required for optimal performance results in very low trade frequency (< 10 events/year per asset), which is a red flag for statistical reliability.

### Crisis Period Performance

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2023)

**Overall Performance**:

- **Sharpe Ratio**: -2.2 (on multi-asset universe) — **severely negative, failing target of >1.5**
- **Total Return**: Negative over full period (ending equity: $37,642 from $100,000)
- **Net Profit**: -$62,357 (fees: -$14,239, representing ~23% of losses)

**Market Regimes Analysis** (from backtest report):

1. **COVID-19 Pandemic (2020)**:

   - Strategy declined consistently (didn't profit during crisis)
   - Mean reversion hypothesis didn't hold during extreme volatility

2. **Post-COVID Run-up (2020-2021)**:

   - Continued decline during strong bull market
   - Failed to benefit from market recovery

3. **Russia Invades Ukraine (2022-2023)**:

   - Continued decline without any recovery

4. **AI Boom / Meme Season (2021)**:
   - No improvement during market enthusiasm

**Key Insight**: Strategy shows consistent decline across all market regimes, suggesting the mean reversion hypothesis doesn't hold in practice. The decline is not steeper during crises, but also doesn't profit during any regime.

### Rolling Performance Stability

**Rolling Sharpe Ratio**: Very stable at around -2.0 (consistently negative)

**Analysis**: Unlike strategies that show volatility in Sharpe ratio, this strategy shows a consistent negative Sharpe of approximately -2.0. The stability is actually a negative indicator — it suggests systematic losses rather than volatility around break-even.

### Generalization Test: In-Sample vs Out-of-Sample

**In-Sample Performance (2018)**:

- **SPY Only**: Sharpe 6.06, optimal parameters from coordinate descent
- **Small Universe (12 stocks)**: Sharpe 1.29, Total Return 11.91%
- **Large Universe (~45 assets)**: Sharpe 1.50, Total Return 18.24%

**Out-of-Sample Performance (2019-2023)**:

- **Large Universe (~45 assets)**: Sharpe -2.2, Total Return negative
- **Ending Equity**: $37,642 (starting $100,000)
- **Win Rate**: ~42%

**Critical Failure**:

- **Observation**: Catastrophic failure in out-of-sample validation despite strong in-sample results
- **Expected**: If strategy captures real mean reversion, it should work across time periods
- **Reality**: Sharp performance reversal indicates **overfitting to in-sample period (2018)**
- **Root Cause**: Strategy likely captured specific patterns in 2018 that don't generalize

**Additional Red Flags**:

- Returns are "mainly flat" with only a few large jumps (low statistical reliability)
- Strategy optimized on 2018 data fails on 2019-2023, indicating overfitting
- Poor performance even before transaction costs (fees only ~23% of total losses)

### Reverse Strategy Test

**Test Design**: Reversed strategy (bet on gap continuation rather than mean reversion)

- **Rationale**: If mean reversion doesn't work, perhaps momentum/continuation does
- **Result**: Even worse performance (Sharpe -2.3, ending equity $32,874)
- **Conclusion**: Neither mean reversion nor momentum hypothesis holds

**Critical Insight**: The failure of both directions suggests the problem is not with the trading direction hypothesis, but with the underlying signal quality or execution costs.

### Root Cause Analysis: Bid-Ask Spread Costs

**Key Finding**: Detailed order analysis reveals bid-ask spread costs are destroying the strategy

**Observation**:

- For most trades, whether buying-then-selling or selling-then-buying, both directions lose money
- This is because of **wider bid-ask spreads at market open**
- Market microstructure: Bid-ask spreads are known to be wider during the opening minutes

**Implication**:

- The strategy's edge (if any) is being overwhelmed by transaction costs
- Wider spreads at market open (9:31-9:45) directly impact entry/exit prices
- This explains why the strategy fails even when mean reversion might theoretically occur

## Risk Analysis

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2023 on multi-asset universe)

### Risk Metrics

| Metric                     | Value    | Interpretation                                                                                     |
| -------------------------- | -------- | -------------------------------------------------------------------------------------------------- |
| **Maximum Drawdown**       | 62.4%    | Cumulative loss from start to end; represents continuous decline rather than isolated events       |
| **Worst Single-Day Loss**  | ~4%      | Reasonable given time-based exit, but frequent daily losses accumulate                             |
| **Correlation to SPY**     | ~0.0     | Average correlation near zero — suggests market-neutral characteristics (as intended)              |
| **Position Concentration** | Variable | Equal weighting across qualifying symbols; number of positions varies daily based on gap frequency |
| **Maximum Leverage**       | 1.0      | No leverage; positions are long or short only (no margin)                                          |
| **Turnover**               | High     | Daily trading with time-based exits; multiple positions per day                                    |

### Risk Controls

Current risk controls implemented in algorithm:

1. **Time-based Exit (9:45 AM)**: Limits intraday exposure by closing positions after 15 minutes
2. **Volatility-based Filtering**: Only trades on statistically unusual gaps (sigma = 10 standard deviations)
3. **Dynamic Position Sizing**: Equal weighting across all qualifying symbols on each day
4. **No Re-entry on Same Day**: One trade per symbol per day (prevents overtrading)

**Missing Risk Controls** (for production):

- Maximum portfolio drawdown circuit breaker
- Daily loss limits
- Stop-loss mechanisms (currently only time-based exits)
- Volatility-based position sizing (currently equal weighting)

## Performance Attribution

### What Drives Returns

**Entry Timing vs Exit Timing**:

- **Entry**: At 9:31 AM (1 minute after market open)
  - **Problem**: Bid-ask spreads are wider at market open, causing slippage
- **Exit**: At 9:45 AM (15 minutes after market open)
  - **Problem**: May exit before mean reversion occurs, or spreads still wide
- **Contribution**: Both entry and exit timing are hurt by wider spreads; transaction costs dominate

**Market Selection vs Individual Stock Selection**:

- **Strategy Design**: Multi-asset universe (12-45 assets) with equal weighting
- **Selection Rationale**: Diversification should reduce variance and increase trade frequency
- **Reality**: Multi-asset universe shows better in-sample performance but fails in out-of-sample

**Concentration Effects**:

- **Observation**: Returns are "sparse jumps and then long flats" (concentrated in few days)
- **Analysis**: This indicates dependence on rare, large-magnitude events rather than consistent edge
- **Risk**: Low statistical reliability; high variance in outcomes

**Return Distribution**:

- **Pattern**: Returns are "mainly flat" with only occasional large jumps
- **Implication**: Strategy relies on rare events rather than consistent edge
- **Root Cause**: Transaction costs (bid-ask spreads) eat into any mean reversion edge

## Limitations & Future Work

### Known Weaknesses

The strategy demonstrates critical weaknesses:

1. **Catastrophic Out-of-Sample Failure**:

   - Severe negative Sharpe ratio (-2.2) on validation period (2019-2023)
   - Ending equity: $37,642 from $100,000 (62.4% drawdown)
   - Evidence of overfitting to in-sample period (2018)

2. **Transaction Cost Issues**:

   - Bid-ask spread costs at market open destroy any potential edge
   - Fees represent ~23% of total losses, but spread costs (implicit) are likely much larger
   - Wider spreads at market open (9:31-9:45) directly hurt entry/exit prices

3. **Low Trade Frequency**:

   - With high sigma (10.0), very few trades per asset (< 10 events/year)
   - Even with multi-asset universe, returns depend on rare events
   - Low statistical reliability due to small sample size

4. **Return Distribution**:
   - Returns depend on rare, large-magnitude events rather than consistent edge
   - "Sparse jumps and then long flats" indicates low reliability

### What Would Be Needed for Production-Ready

**This strategy is currently not usable** due to:

- Catastrophic out-of-sample failure
- Transaction costs overwhelming any edge
- Evidence of overfitting to training period

**Improvements Required**:

1. **Transaction Cost Management**:

   - Account for bid-ask spreads at market open (currently not modeled in optimizer)
   - Consider entering later in day when spreads narrow
   - Implement limit orders to control entry/exit prices

2. **Signal Quality**:

   - Investigate why mean reversion doesn't hold in practice
   - Consider cross-sectional gap analysis (relative gaps across assets)
   - Explore additional filters beyond volatility (volume, news sentiment)

3. **Parameter Robustness**:

   - Test walk-forward optimization instead of single-period optimization
   - Validate on completely different time periods (different decades)
   - Consider regime-dependent parameters

4. **Risk Management**:
   - Add portfolio-level risk controls (max drawdown circuit breaker, daily loss limits)
   - Implement stop-loss mechanisms beyond time-based exits
   - Consider volatility-based position sizing

### Key Learnings

**What Didn't Work**:

- Mean reversion hypothesis doesn't hold in practice (strategy fails in both directions)
- Transaction costs (bid-ask spreads) destroy any potential edge
- Optimization led to overfitting to 2018-specific patterns
- Returns are flat/reliant on rare events rather than consistent edge

**Critical Insight**: A strategy that shows strong in-sample performance but fails catastrophically out-of-sample, with both mean reversion and momentum hypotheses failing, suggests the edge was illusory. The root cause appears to be transaction costs (bid-ask spreads at market open) overwhelming any theoretical mean reversion edge. This highlights the importance of:

- Modeling realistic transaction costs (not just fees, but spreads)
- Testing strategies in both directions (mean reversion and momentum)
- Out-of-sample validation on completely different time periods
- Understanding market microstructure effects (spread timing, liquidity)
