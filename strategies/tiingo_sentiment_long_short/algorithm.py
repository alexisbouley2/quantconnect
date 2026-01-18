# region imports
from AlgorithmImports import *
from typing import Dict, List
# endregion

import numpy as np

class TiingoSentimentLS(QCAlgorithm):
    """
    Tiingo News Sentiment Long-Short Strategy - QuantConnect Implementation
    
    This algorithm implements a market-neutral long-short strategy based on news sentiment analysis:
    1. Analyzes Tiingo news articles for sentiment using keyword-based scoring
    2. Ranks stocks by aggregated sentiment scores (with recency weighting)
    3. Goes long the top N/2 stocks (most positive sentiment)
    4. Goes short the bottom N/2 stocks (most negative sentiment)
    5. Rebalances daily to maintain market-neutral exposure
    
    The strategy aims to capture alpha from news-driven price movements while remaining
    market-neutral through equal long/short allocation.
    """

    def initialize(self) -> None:
        """
        Initialize the algorithm: set dates, cash, universe, and schedule rebalancing.
        """
        # Backtest configuration
        self.set_start_date(2018, 1, 1)
        self.set_end_date(2019, 1, 1)
        self.set_cash(100000)
        
        # Strategy parameters
        self.max_positions: int = 10  # Total positions: top 5 long + bottom 5 short
        self.cash_margin: float = 0.03  # Keep 3% cash margin (97% deployed)
        
        # Initialize universe: liquid large-cap stocks across multiple sectors
        # Selected for: high liquidity, comprehensive news coverage, market representation
        tickers = [
            # Tech: Large-cap technology stocks
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'ADBE', 'CRM',
            # Finance: Major banks and financial services
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW',
            # Healthcare: Pharmaceuticals and health services
            'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'CVS',
            # Consumer: Retail and consumer goods
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'NKE', 'MCD', 'SBUX',
            # Energy: Oil and gas companies
            'XOM', 'CVX', 'COP', 'SLB',
            # Industrials: Manufacturing and logistics
            'BA', 'CAT', 'GE', 'UPS', 'HON',
            # ETFs: Major indices for diversification
            'SPY', 'QQQ', 'IWM', 'DIA'
        ]
        
        # Map equity symbols to their corresponding Tiingo news data symbols
        # This allows us to fetch news articles for each stock
        self._dataset_symbols: Dict[Symbol, Symbol] = {}
        for ticker in tickers:
            symbol: Symbol = self.add_equity(ticker, Resolution.DAILY).symbol
            news_symbol: Symbol = self.add_data(TiingoNews, symbol).symbol
            self._dataset_symbols[symbol] = news_symbol
        
        # News analysis parameters
        self.news_days: int = 7  # Look back 7 trading days for news articles
        
        # Warm up period: 30 days to build initial news history
        self.set_warm_up(30, Resolution.DAILY)
        
        # Schedule daily rebalancing: 30 minutes after market open
        # This allows market to settle after opening volatility
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.after_market_open("SPY", 30),
            self._rebalance
        )

        # Keyword-based sentiment scoring dictionary
        # Simple lexicon approach: positive words = +0.5, negative words = -0.5
        # Note: This is a simplified sentiment analysis. More sophisticated methods
        # (sentence encoders, LLMs, sentiment models) could improve accuracy.
        self.word_scores: Dict[str, float] = {
            "bad": -0.5, "good": 0.5, "negative": -0.5, 
            "great": 0.5, "growth": 0.5, "fail": -0.5, 
            "failed": -0.5, "success": 0.5, "nailed": 0.5,
            "beat": 0.5, "missed": -0.5, "profitable": 0.5,
            "beneficial": 0.5, "right": 0.5, "positive": 0.5, 
            "large": 0.5, "attractive": 0.5, "sound": 0.5, 
            "excellent": 0.5, "wrong": -0.5, "unproductive": -0.5, 
            "lose": -0.5, "missing": -0.5, "mishandled": -0.5, 
            "un_lucrative": -0.5, "up": 0.5, "down": -0.5,
            "worthwhile": 0.5, "lucrative": 0.5, "solid": 0.5
        }

    def _rebalance(self) -> None:
        """
        Daily rebalancing function: calculate sentiment scores, rank stocks, and rebalance positions.
        
        Process:
        1. Calculate sentiment score for each stock based on recent news articles
        2. Rank stocks by sentiment (highest to lowest)
        3. Go long top N/2 stocks (most positive sentiment)
        4. Go short bottom N/2 stocks (most negative sentiment)
        5. Liquidate positions that no longer qualify
        """
        if self.is_warming_up:
            return
        
        sentiment_scores: Dict[Symbol, float] = {}
        
        # Step 1: Calculate sentiment score for each symbol
        for symbol, news_symbol in self._dataset_symbols.items():
            # Fetch news articles from last N trading days
            articles = self.history[TiingoNews](news_symbol, self.news_days, Resolution.DAILY)

            # Filter articles for this specific symbol (Tiingo news may contain multiple symbols)
            article_texts: List[str] = [
                article.description 
                for article in articles 
                if article.symbol.underlying == symbol
            ]
            
            # Skip symbols with no news coverage
            if not article_texts:
                continue
            
            # Step 2: Calculate sentiment score for each article using keyword matching
            scores: List[float] = []
            for article_text in article_texts:
                words: List[str] = article_text.lower().split(" ")
                # Sum sentiment scores for matching keywords
                score: float = sum([
                    self.word_scores[word] 
                    for word in words 
                    if word in self.word_scores
                ])
                scores.append(score)
            
            # Step 3: Aggregate article scores with exponential recency weighting
            # More recent articles have higher weight
            net_sentiment: float = self._aggregate_sentiment_scores(scores)
            sentiment_scores[symbol] = net_sentiment
        
        # Step 4: Validate we have enough symbols with sentiment data
        if len(sentiment_scores) < self.max_positions:
            self.log(f"WARNING: Only {len(sentiment_scores)} symbols with sentiment (need {self.max_positions})")
            return
        
        # Step 5: Rank stocks by sentiment (highest to lowest)
        sorted_symbols = sorted(sentiment_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Step 6: Select top N/2 for long positions, bottom N/2 for short positions
        # This creates a market-neutral portfolio (equal long/short allocation)
        long_symbols: List[Symbol] = [s[0] for s in sorted_symbols[:self.max_positions//2]]
        short_symbols: List[Symbol] = [s[0] for s in sorted_symbols[-self.max_positions//2:]]
        
        # Step 7: Liquidate positions that no longer qualify or have flipped direction
        for kvp in self.portfolio:
            symbol: Symbol = kvp.key
            holding = kvp.value
            
            # Skip if not currently invested
            if not holding.invested:
                continue
            
            should_liquidate: bool = False
            
            # Liquidate if: symbol no longer in top/bottom ranks, OR position direction flipped
            if symbol not in long_symbols and symbol not in short_symbols:
                should_liquidate = True  # Symbol fell out of top/bottom rankings
            elif symbol in long_symbols and holding.is_short:
                should_liquidate = True  # Was short, now should be long
            elif symbol in short_symbols and holding.is_long:
                should_liquidate = True  # Was long, now should be short
            
            if should_liquidate:
                self.liquidate(symbol)
        
        # Step 8: Calculate equal weights for new positions
        # Equal weighting within long and short sides (with cash margin)
        long_weight: float = (1.0 - self.cash_margin) / (self.max_positions // 2)
        short_weight: float = -(1.0 - self.cash_margin) / (self.max_positions // 2)  # Negative for short
        
        # Step 9: Enter new long positions
        for symbol in long_symbols:
            self.set_holdings(symbol, long_weight)
        
        # Step 10: Enter new short positions
        for symbol in short_symbols:
            self.set_holdings(symbol, short_weight)

    def _aggregate_sentiment_scores(self, sentiment_scores: List[float]) -> float:
        """
        Aggregate individual article sentiment scores with exponential recency weighting.
        
        More recent articles receive higher weight, as news impact decays over time.
        Uses exponential weighting: weights increase exponentially from oldest to newest article.
        
        Args:
            sentiment_scores: List of sentiment scores for individual articles (ordered by date)
        
        Returns:
            Weighted average sentiment score across all articles
        
        Example:
            If articles have scores [1.0, 2.0, 3.0] (oldest to newest),
            the newest article (3.0) gets the highest weight.
        """
        n: int = len(sentiment_scores)
        
        if n == 0:
            return 0.0
        
        # Generate exponential weights: newer articles get exponentially higher weights
        # np.linspace(0, 1, n) creates equal spacing, np.exp() creates exponential growth
        weights: np.ndarray = np.exp(np.linspace(0, 1, n))
        weights /= weights.sum()  # Normalize to sum to 1.0
        
        # Return weighted sum of sentiment scores
        return float(np.sum(np.array(weights) * np.array(sentiment_scores)))