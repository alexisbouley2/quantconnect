# Quantitative Trading Strategy Research

This repository contains quantitative trading strategies developed and backtested using the QuantConnect platform. Each strategy follows a systematic research, optimization, and validation workflow to evaluate trading edge and robustness.

## Project Scope & Objectives

The goal of this project is to develop, test, and analyze algorithmic trading strategies across different market phenomena:

- **Research & Development**: Systematic approach to strategy development with parameter optimization
- **Robustness Testing**: In-sample optimization, out-of-sample validation, and generalization tests
- **Critical Analysis**: Honest evaluation of strategy performance, limitations, and production-readiness
- **Documentation**: Comprehensive analysis of economic rationale, methodology, and results

Each strategy is evaluated for:

- Risk-adjusted returns (Sharpe ratio)
- Robustness across assets and time periods
- Parameter sensitivity
- Market regime performance
- Production-readiness

## Repository Structure

```
quantconnect/
├── strategies/              # Individual trading strategies
│   ├── opening_range_breakout/
│   ├── overnight_gap_mean_reverse/
│   ├── tiingo_sentiment_long_short/
├── utils/                  # Testing and optimization utilities
│   ├── tester.py          # Strategy backtesting framework
│   └── parameter_optimizer.py  # Coordinate descent optimization
├── research/              # Additional research notebooks
└── README.md             # This file
```

### Strategy Folder Structure

Each strategy folder contains:

- **`algorithm.py`**: Production-ready QuantConnect algorithm implementation
- **`analysis.md`**: Comprehensive strategy analysis document
  - Executive Summary
  - Economic Rationale
  - Methodology
  - Robustness Analysis
  - Risk Analysis
  - Performance Attribution
  - Limitations & Future Work
- **`backtest-report.pdf`**: QuantConnect out-of-sample validation report
- **`backtest-report-training.pdf`**: In-sample training report (if available)
- **`research*.ipynb`**: Jupyter notebooks for parameter optimization and research
- **`variants/`**: Alternative strategy implementations for comparison

### Utility Tools

- **`tester.py`**: Custom backtesting framework for pre-validation research (no transaction costs)
- **`parameter_optimizer.py`**: Coordinate descent optimization for parameter tuning

## Strategy Summary

### 1. Opening Range Breakout Strategy

**Concept**: Capture momentum from price breakouts beyond the opening range (first 30 minutes) using a trailing stop mechanism.

**Key Features**:

- Entry: Price breaks above/below opening range + buffer threshold
- Exit: Trailing stop based on price percentage (1% reversion) or time-based (15:45)
- Two variants tested: Volatility-based vs. Price-percentage trailing stops

**Results**:

- **In-Sample (2018)**: Sharpe 2.69 on SPY
- **Out-of-Sample (2019-2023)**: Sharpe -0.4 on multi-asset universe
- **Status**: ❌ Not production-ready

**Key Findings**:

- Failed to generalize beyond SPY (Sharpe 2.69 → 0.97 on multi-asset)
- High parameter sensitivity to `breakout_buffer`
- Evidence of overfitting to training period
- Performance degradation indicates lack of robustness

**Files**: `strategies/opening_range_breakout/`

---

### 2. Overnight Gap Mean Reversion Strategy

**Concept**: Profit from mean reversion of unusual overnight price gaps by betting that large gaps revert during regular market hours.

**Key Features**:

- Entry: Identify gaps exceeding volatility threshold (10 standard deviations) at 9:31 AM
- Direction: Fade the gap (short upward gaps, long downward gaps)
- Exit: Time-based exit at 9:45 AM (15 minutes after market open)

**Results**:

- **In-Sample (2018)**: Sharpe 6.06 on SPY
- **Out-of-Sample (2019-2023)**: Sharpe -2.2, -62.4% drawdown
- **Status**: ❌ Not production-ready

**Key Findings**:

- Catastrophic out-of-sample failure despite strong in-sample results
- Bid-ask spread costs at market open destroy any potential edge
- Returns depend on rare events (< 10 trades/year per asset)
- Reverse strategy test (momentum) also failed, indicating fundamental issues

**Files**: `strategies/overnight_gap_mean_reverse/`

---

### 3. Tiingo News Sentiment Long-Short Strategy

**Concept**: Market-neutral long-short strategy based on news sentiment analysis. Rank stocks by sentiment, go long most positive and short most negative.

**Key Features**:

- Sentiment Analysis: Keyword-based scoring of Tiingo news articles over 7-day rolling window
- Ranking: Sort stocks by aggregated sentiment (with exponential recency weighting)
- Positioning: Long top 5 stocks, short bottom 5 stocks (market-neutral)
- Rebalancing: Daily rebalancing 30 minutes after market open

**Results**:

- **Training (2018)**: Positive returns
- **Out-of-Sample (2019-2022)**: Highly volatile with 34.5% drawdown
- **Status**: ⚠️ Requires significant improvements

**Key Findings**:

- **Strong crisis performance**: +50% during COVID crash, +60% during Russia-Ukraine
- **Poor stability**: Flat periods, 34.5% drawdown in 2021 bull market
- **Market correlation**: Beta ≈ -0.2 despite intended market-neutral design
- **Regime dependence**: Performs well in crises but fails in normal/bull markets

**Main Issues**:

- Simple keyword-based sentiment analysis lacks nuance
- Negative market correlation suggests flawed long/short selection
- Parameter sensitivity to `max_positions`

**Files**: `strategies/tiingo_sentiment_long_short/`

---

## Research Workflow

1. **Strategy Development**: Implement strategy variants in `variants/` folder
2. **Parameter Optimization**: Use `research*.ipynb` notebooks with coordinate descent optimization
3. **Pre-Validation**: Test without transaction costs using `tester.py` framework
4. **QuantConnect Validation**: Submit `algorithm.py` to QuantConnect for realistic backtesting
5. **Analysis**: Document findings, limitations, and production-readiness in `analysis.md`

## Key Learnings

### What Works

- Systematic research process with clear documentation
- Pre-validation testing framework (transaction-cost free)
- Honest evaluation of strategy limitations

### Common Pitfalls Observed

1. **Overfitting**: Strong in-sample performance that doesn't generalize
2. **Transaction Costs**: Strategies fail when realistic costs are applied
3. **Market Regime Dependence**: Performance varies dramatically across market conditions
4. **Parameter Sensitivity**: Over-optimization leads to fragile strategies
5. **Generalization Failure**: Single-asset optimization doesn't extend to broader universes

### Best Practices Applied

- Separate in-sample optimization from out-of-sample validation
- Test generalization across multiple assets
- Evaluate performance across different market regimes
- Document limitations and failure modes honestly
- Implement robust risk controls (where applicable)

## Technologies & Tools

- **QuantConnect**: Cloud-based algorithmic trading platform
- **Python**: Strategy implementation and research
- **Jupyter Notebooks**: Parameter optimization and research
- **Pandas/NumPy**: Data analysis and optimization

## Future Directions

- Enhanced sentiment analysis (sentence encoders, LLMs)
- Improved risk management (stop-losses, drawdown circuit breakers)
- Cross-sectional momentum strategy completion
- Walk-forward optimization for better robustness
- Real-time execution framework

---

**Note**: All strategies in this repository are for research and educational purposes. Results are based on historical backtesting and do not guarantee future performance. Transaction costs, slippage, and market impact can significantly affect real-world results.
