from AlgorithmImports import *
import numpy as np

class TiingoSentimentLS(QCAlgorithm):

    def initialize(self):
        self.set_start_date(2018, 1, 1)
        self.set_end_date(2019, 1, 1)
        self.set_cash(100000)
        self.max_positions = 10
        self.cash_margin = 0.03
        # self.max_positions = 30
        # self.cash_margin = 0.01
        
        # Initialize with liquid large-cap stocks (won't change during backtest)
        tickers = [
            # Tech
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA', 'NFLX', 'ADBE', 'CRM',
            # Finance
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'SCHW',
            # Healthcare
            'JNJ', 'UNH', 'PFE', 'ABBV', 'TMO', 'MRK', 'CVS',
            # Consumer
            'WMT', 'HD', 'PG', 'KO', 'PEP', 'NKE', 'MCD', 'SBUX',
            # Energy
            'XOM', 'CVX', 'COP', 'SLB',
            # Industrials
            'BA', 'CAT', 'GE', 'UPS', 'HON',
            # ETFs for diversification
            'SPY', 'QQQ', 'IWM', 'DIA'
        ]
        
        # Add all securities at start
        self._dataset_symbols = {}
        for ticker in tickers:
            symbol = self.add_equity(ticker, Resolution.DAILY).symbol
            news_symbol = self.add_data(TiingoNews, symbol).symbol
            self._dataset_symbols[symbol] = news_symbol
        
        # Configuration
        self.news_days = 7
        
        # Warm up all stocks together
        self.set_warm_up(30, Resolution.DAILY)
        
        # Trade daily after warm up
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.after_market_open("SPY", 30),
            self._rebalance
        )

        self.word_scores = {
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

    def _rebalance(self):
        if self.is_warming_up:
            return
        
        sentiment_scores = {}
        
        # Calculate sentiment for each symbol
        for symbol, news_symbol in self._dataset_symbols.items():
            # Fetch news from last 7 trading days
            articles = self.history[TiingoNews](news_symbol, self.news_days, Resolution.DAILY)

            # Filter for this symbol
            article_texts = [
                article.description 
                for article in articles 
                if article.symbol.underlying == symbol
            ]
            
            if not article_texts:
                continue
            
            # Calculate sentiment scores
            scores = []
            for article_text in article_texts:
                words = article_text.lower().split(" ")
                score = sum([self.word_scores[word] for word in words if word in self.word_scores])
                scores.append(score)
            
            # Aggregate with recency weighting
            net_sentiment = self._aggregate_sentiment_scores(scores)
            sentiment_scores[symbol] = net_sentiment
        
        # Check if we have enough symbols
        if len(sentiment_scores) < self.max_positions:
            self.log(f"WARNING: Only {len(sentiment_scores)} symbols with sentiment (need {self.max_positions})")
            return
        
        # Sort by sentiment
        sorted_symbols = sorted(sentiment_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Top 5 for long, bottom 5 for short
        long_symbols = [s[0] for s in sorted_symbols[:self.max_positions//2]]
        short_symbols = [s[0] for s in sorted_symbols[-self.max_positions//2:]]
        
        # Liquidate old/flipped positions
        for kvp in self.portfolio:
            symbol = kvp.key
            holding = kvp.value
            
            if not holding.invested:
                continue
            
            should_liquidate = False
            
            if symbol not in long_symbols and symbol not in short_symbols:
                should_liquidate = True
            elif symbol in long_symbols and holding.is_short:
                should_liquidate = True
            elif symbol in short_symbols and holding.is_long:
                should_liquidate = True
            
            if should_liquidate:
                self.liquidate(symbol)
        
        # Calculate weights
        long_weight = (1.0 - self.cash_margin) / (self.max_positions // 2)
        short_weight = -(1.0 - self.cash_margin) / (self.max_positions // 2)
        
        # Enter positions
        for symbol in long_symbols:
            self.set_holdings(symbol, long_weight)
        
        for symbol in short_symbols:
            self.set_holdings(symbol, short_weight)

    def _aggregate_sentiment_scores(self, sentiment_scores):
        n = len(sentiment_scores)
        
        if n == 0:
            return 0
        
        weights = np.exp(np.linspace(0, 1, n))
        weights /= weights.sum()
        
        return np.sum(np.array(weights) * np.array(sentiment_scores))