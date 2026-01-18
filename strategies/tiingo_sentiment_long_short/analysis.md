# Tiingo News Sentiment Long-Short Strategy - Analysis

## Executive Summary

The Tiingo News Sentiment Long-Short strategy attempts to capture alpha from news-driven price movements by ranking stocks based on keyword-based sentiment analysis of Tiingo news articles. The strategy goes long the stocks with most positive sentiment and short those with most negative sentiment, maintaining market-neutral exposure through equal long/short allocation. While the strategy showed strong performance during crisis periods (COVID-19, Russia-Ukraine), it demonstrated significant instability with flat periods, a 34.5% drawdown in 2021, and negative correlation to the market (beta ≈ -0.2) despite the intended market-neutral design. **Conclusion**: The strategy shows promise during volatile/crisis periods but lacks robustness due to inconsistent performance, market dependence issues, and parameter sensitivity. Significant improvements in sentiment analysis methodology and risk controls are needed for production use.

## Economic Rationale

**Hypothesis**: Markets are news/events-driven. Tiingo produces enterprise-grade news and analysis. By analyzing the most positive news (long) and shorting the most negative news (short), we aim to create a market-neutral, robust strategy that captures sentiment-driven price movements.

**Market Microstructure Explanation**:

- **News Impact**: Corporate news and analysis drive price movements as markets incorporate new information
- **Sentiment Persistence**: Positive/negative sentiment from news articles can persist over several days
- **Relative Positioning**: By ranking stocks relative to each other, we capture cross-sectional sentiment differences

**Behavioral Drivers**:

- **Information Diffusion**: News sentiment affects investor behavior and stock prices
- **Sentiment Momentum**: Positive news begets positive price movements (and vice versa)
- **Market Efficiency**: Sentiment-driven mispricings may exist before full market incorporation

**Strategy Logic**:

1. **Data Collection**: Gather Tiingo news articles for each stock over rolling 7-day window
2. **Sentiment Scoring**: Calculate keyword-based sentiment scores for each article
3. **Aggregation**: Weight recent articles more heavily (exponential recency weighting)
4. **Ranking**: Sort all stocks by aggregated sentiment score
5. **Positioning**: Long top N/2 stocks, short bottom N/2 stocks (market-neutral)
6. **Rebalancing**: Daily rebalancing at 30 minutes after market open

## Methodology

### Data & Universe

- **Universe**: ~50 US large-cap stocks across sectors (Tech, Finance, Healthcare, Consumer, Energy, Industrials) plus major ETFs (SPY, QQQ, IWM, DIA)
- **Selection Rationale**:
  - High liquidity (essential for shorting)
  - Comprehensive news coverage (Tiingo analysis available)
  - Sector diversification (robust to sector-specific risks)
  - Market representation (major indices and sector leaders)
- **Resolution**: Daily (rebalance once per day)
- **Data Sources**: Tiingo news articles (enterprise-grade news and analysis)
- **Backtest Period**: 2018 (training/in-sample); 2019-2022 (out-of-sample validation)

### Entry Logic

**Sentiment Calculation Process**:

1. **Article Retrieval**: For each stock, fetch all news articles from the last 7 trading days
2. **Keyword Scoring**: For each article, calculate sentiment score using keyword dictionary:
   - Positive keywords (e.g., "good", "growth", "success", "beat") → +0.5
   - Negative keywords (e.g., "bad", "fail", "missed", "lose") → -0.5
   - Score = sum of matching keyword scores
3. **Recency Weighting**: Aggregate article scores using exponential weighting:
   - More recent articles receive exponentially higher weights
   - Formula: `weights = exp(linspace(0, 1, n)) / sum(exp(...))`
   - Net sentiment = weighted sum of all article scores

**Entry Conditions**:

- Stocks ranked by aggregated sentiment score (highest to lowest)
- **Long Positions**: Top `max_positions/2` stocks (most positive sentiment)
- **Short Positions**: Bottom `max_positions/2` stocks (most negative sentiment)
- Entry at 30 minutes after market open (allows market to settle)

### Exit Logic

**Dynamic Exit Based on Rankings**:

- **No Time-Based Exits**: Positions held until ranking changes
- **Exit Conditions**: Liquidate a position if:
  1. Stock falls out of top/bottom `max_positions/2` rankings, OR
  2. Stock flips from long to short (or vice versa) based on new sentiment
- **Daily Rebalancing**: Portfolio rebalanced daily to reflect current sentiment rankings

**Rationale**: Exit only when sentiment ranking changes, allowing positions to run if sentiment remains consistent.

### Position Sizing

- **Equal Weighting**: Equal allocation within long side and within short side
- **Cash Margin**: Maintain 3% cash margin (97% of capital deployed)
- **Long Weight**: `(1.0 - cash_margin) / (max_positions // 2)` per long position
- **Short Weight**: `-(1.0 - cash_margin) / (max_positions // 2)` per short position (negative for short)
- **Market Neutrality**: Equal total long exposure and short exposure (offsetting market risk)

### Parameters

Final parameters (after testing on training benchmark):

| Parameter       | Value | Justification                                                                                            |
| --------------- | ----- | -------------------------------------------------------------------------------------------------------- |
| `news_days`     | 7     | Look back 7 trading days for news; maximum expected duration for article impact on stock prices          |
| `max_positions` | 10    | Total positions: 5 long + 5 short; optimal balance between risk spread and focusing on strongest signals |
| `cash_margin`   | 0.03  | 3% cash margin (97% deployed); provides buffer for margin requirements                                   |

**Parameter Selection Method**: Empirical testing on training benchmark (2018)

**Parameter Sensitivity**:

- **`news_days`**: Fixed at 7 days (theoretical maximum expected impact duration)
- **`max_positions`**: **High sensitivity** — performance strongly changes depending on top/bottom decile selection
  - Fewer positions = stronger signals but higher concentration risk
  - More positions = diversification but dilutes signal quality
  - Optimal value of 10 was empirically determined for ~50 stock universe

## Robustness Analysis

### Performance Instability

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2022)

**Critical Finding**: Strategy shows extreme performance instability with inconsistent behavior across periods

**Performance Timeline**:

1. **Jan 2019 - Jan 2020**: Flat period (no significant returns)
2. **Jan 2020 - April 2020**: **Brutal spike (+50%)** during COVID-19 market crash
3. **April 2020 - October 2020**: Flat with high volatility
4. **October 2020 - October 2021**: **Massive drawdown (-34.5%)** — biggest red flag
5. **October 2021 - September 2022**: **Huge increase (+100% returns)** during Russia-Ukraine period

**Year-by-Year Behavior**:

- **2018** (training): Small positive returns
- **2019**: Flat period
- **2020**: High spike during COVID crash, then flat during recovery
- **2021**: Significant negative returns (drawdown)
- **2022**: Large positive returns (Russia-Ukraine period)

**Analysis**: The extreme volatility and regime-dependent performance suggest the strategy is highly sensitive to market conditions rather than consistently capturing sentiment edge. The 34.5% drawdown in 2021 is particularly concerning.

### Market Dependence

**Critical Finding**: Strategy shows negative correlation to market despite intended market-neutral design

**Market Beta Analysis**:

- **Rolling Portfolio Beta to SPY**: Oscillates around **-0.2** (slightly negative)
- **Expected**: Beta should be close to 0 (market-neutral)
- **Reality**: Consistent negative beta indicates strategy behaves inversely to market trends

**Market Regime Observations**:

- **2021 (Strong Bull Market)**: Strategy experienced its **biggest drawdown (-34.5%)**
  - Market was steadily improving
  - Strategy negatively anticipated which stocks would perform better (sentiment signals were wrong)
- **COVID-19 Crash (2020)**: Strategy performed well (+50% spike) when market was falling
  - Survived COVID with strong returns during market decline
  - 6-month rolling Sharpe ratio reached -0.5 during this period (temporarily)

**Potential Explanations**:

1. **Crisis vs Normal Markets**:

   - During crises (COVID, Russia-Ukraine), it may be easier to identify which stocks will be most impacted
   - In normal markets, dominant news is less clear, making sentiment signals less reliable
   - This explains good performance during crises but not the negative performance in 2021

2. **Sentiment Bias**:

   - Negative sentiment correlation may indicate that positive news stocks underperform in bull markets
   - Or short-side selection is flawed (shorting negative sentiment stocks that actually perform well)

3. **Market Neutrality Failure**:
   - Despite equal long/short allocation, the strategy is not truly market-neutral
   - Long/short imbalance in sentiment quality may create unintended market exposure

**Improvement Idea**: To improve market neutrality, consider asymmetrical allocation (e.g., 100% long / 50% short) or dynamic long/short ratio based on aggregate market sentiment.

### Crisis Period Performance

**COVID-19 Pandemic (2020)**:

- **High Spike**: +50% return when market was falling (Jan-April 2020)
- **During Recovery**: Performances stagnating with high volatility (April-October 2020)
- **Analysis**: Strategy captured crisis-driven sentiment differences but failed during recovery period

**Post-COVID Run-up (2020-2021)**:

- **Negative Performance**: Strategy underperformed during bull market recovery
- **Root Cause**: Negatively anticipated which stocks would behave better (sentiment signals were incorrect)
- **Biggest Drawdown**: -34.5% from October 2020 to October 2021

**Russia Invades Ukraine (2022-2023)**:

- **Strong Performance**: Return of more than +60% in 10 months
- **Analysis**: Crisis period again favored the strategy (similar to COVID pattern)

**Key Insight**: Strategy performs well during crisis/volatile periods but struggles in normal/bull markets, suggesting it captures crisis-specific sentiment patterns rather than consistent alpha.

### Parameter Sensitivity

**`max_positions` Sensitivity**:

- **Finding**: Performance strongly changes depending on top/bottom decile selection
- **Rationale**: This is expected because `max_positions` determines the main edge (knowing which stocks have positive news relative to others with negative news)
- **Implication**: High parameter sensitivity suggests strategy may be overfitting to specific decile thresholds

**Analysis**: The sensitivity to `max_positions` is a red flag for robustness. The optimal value (10 positions) may not generalize to different market regimes.

## Risk Analysis

Reference: `backtest-report.pdf` (QuantConnect validation: 2019-2022)

### Risk Metrics

| Metric                     | Value    | Interpretation                                                                                              |
| -------------------------- | -------- | ----------------------------------------------------------------------------------------------------------- |
| **Maximum Drawdown**       | 34.5%    | Occurred during 2021 bull market; represents strategy failure in normal market conditions                   |
| **Worst Single-Day Loss**  | ~8%      | Occurred during COVID pandemic; high volatility during crisis periods                                       |
| **Correlation to SPY**     | -0.2     | Negative correlation despite intended market-neutral design; indicates strategy behaves inversely to market |
| **Position Concentration** | High     | 100% deployed (97% after cash margin); equal weighting among 5 long positions and 5 short positions         |
| **Maximum Leverage**       | ~1.0     | Approximately 1x leverage (100% long + 100% short = 200% gross exposure, net 0% market exposure)            |
| **Turnover**               | Moderate | Daily rebalancing; positions change as sentiment rankings shift                                             |

### Risk Controls

**Current Risk Controls in Algorithm**:

- **None**: The strategy lacks explicit risk controls

**Missing Risk Controls** (for production):

- Time-based exits (prevents overnight risk)
- Position size limits (beyond equal weighting)
- Stop-loss mechanisms
- Maximum drawdown circuit breaker
- Daily loss limits
- Correlation limits (to ensure market neutrality)
- Volatility-based position sizing

## Performance Attribution

### What Drives Returns

**Crisis and Bear Market Performance**:

- **Observation**: Strongest performance occurs during crisis/volatile periods (COVID crash, Russia-Ukraine)
- **Hypothesis**: During crises, sentiment differences between stocks are more pronounced and easier to identify
- **Risk**: Strategy may be overfitting to crisis-specific patterns rather than capturing consistent sentiment edge

**Entry Timing vs Exit Timing**:

- **Entry**: 30 minutes after market open (allows market to settle)
- **Exit**: Dynamic based on sentiment ranking changes (positions held until ranking shifts)
- **Contribution**: Difficult to isolate, but dynamic exits allow positions to run if sentiment persists

**Market Selection vs Individual Stock Selection**:

- **Strategy Design**: Relative ranking approach (comparing stocks to each other)
- **Reality**: Strategy performance is highly regime-dependent (crisis vs normal markets)
- **Issue**: Market regime appears to drive returns more than individual stock selection quality

**Concentration Effects**:

- **Position Concentration**: Only 5 long + 5 short positions from ~50 stock universe
- **Rationale**: Focuses on strongest sentiment signals
- **Risk**: High concentration increases volatility and drawdown risk (34.5% drawdown)

**Sentiment Analysis Quality**:

- **Current Method**: Simple keyword matching (dictionary-based)
- **Limitation**: May miss nuanced sentiment, context, or sarcasm
- **Impact**: Low-quality sentiment signals may contribute to poor performance in normal markets

## Limitations & Future Work

### Known Weaknesses

1. **Performance Instability**:

   - Extreme volatility with flat periods and large spikes/drawdowns
   - 34.5% maximum drawdown in 2021 (strategy failure during bull market)
   - Inconsistent behavior across different market regimes

2. **Market Dependence Issues**:

   - Negative correlation to market (beta ≈ -0.2) despite intended market-neutral design
   - Poor performance during bull markets (2021 drawdown)
   - Strong performance during crises suggests crisis-specific overfitting

3. **Parameter Sensitivity**:

   - High sensitivity to `max_positions` parameter
   - Optimal parameters may not generalize across market regimes

4. **Sentiment Analysis Limitations**:

   - Simple keyword matching lacks nuance and context
   - May miss sophisticated sentiment signals
   - No consideration of sentence structure or article tone

5. **Lack of Risk Controls**:
   - No stop-loss mechanisms
   - No maximum drawdown protection
   - No daily loss limits

### What Would Be Needed for Production-Ready

**This strategy is currently not production-ready** due to:

- Extreme performance instability
- Market dependence issues (negative correlation)
- Lack of risk controls
- Parameter sensitivity

**Improvements Required**:

1. **Sentiment Analysis Enhancement**:

   - **Current**: Keyword-based dictionary matching
   - **Proposed**: Use sentence encoders, sentiment analysis models, or LLMs for more sophisticated sentiment extraction
   - **Rationale**: Better sentiment quality may improve signal reliability across market regimes

2. **Market Neutrality Fixes**:

   - **Issue**: Negative correlation to market (beta ≈ -0.2) despite equal long/short allocation
   - **Proposed**:
     - Asymmetrical allocation (e.g., 100% long / 50% short)
     - Dynamic long/short ratio based on aggregate market sentiment
     - Use raw article scores to detect bear/bull markets and adjust ratio accordingly

3. **Cross-Sectional vs Absolute Sentiment**:

   - **Current**: Only relatively compares assets to each other
   - **Proposed**: Use raw article scores to detect overall market sentiment (bear/bull markets)
   - **Application**: Adjust long/short ratio or position sizing based on aggregate market sentiment

4. **Risk Management**:

   - Add stop-loss mechanisms for individual positions
   - Implement maximum drawdown circuit breaker
   - Add daily loss limits
   - Consider volatility-based position sizing

5. **Parameter Robustness**:

   - Test `max_positions` sensitivity across different market regimes
   - Consider dynamic parameter adjustment based on market conditions
   - Validate on completely different time periods (different decades)

6. **Exit Logic Improvements**:
   - Consider time-based exits to limit exposure duration
   - Implement trailing stops for individual positions
   - Add position-level risk controls

### Key Learnings

**What Worked**:

- Strong performance during crisis periods (COVID, Russia-Ukraine)
- Market-neutral framework provides foundation for systematic approach
- Daily rebalancing allows adaptation to changing sentiment

**What Didn't Work**:

- Poor performance stability (flat periods, large drawdowns)
- Negative correlation to market despite intended market neutrality
- Inconsistent performance across market regimes
- Simple keyword-based sentiment analysis is insufficient

**Critical Insight**: A sentiment-based long-short strategy that performs well during crises but fails in normal markets suggests it's capturing crisis-specific patterns rather than consistent sentiment edge. The negative market correlation despite equal long/short allocation indicates fundamental issues with the sentiment selection or market neutrality mechanism. Significant improvements in sentiment analysis methodology and risk controls are essential for production use.
