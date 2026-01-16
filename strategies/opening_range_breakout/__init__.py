# region imports
from AlgorithmImports import *
# endregion

"""
Opening Range Breakout Strategy Variants

This package contains different variants of the opening range breakout strategy:

- variant_1: Reversion threshold based on opening range volatility
  (reversion_threshold = or_range * reversion_multiple)
  
- variant_2: Reversion threshold based on price percentage
  (reversion_threshold = high_water_mark * reversion_multiple)
"""

from .variant_1 import opening_range_breakout as variant_1
from .variant_2 import opening_range_breakout as variant_2

__all__ = ['variant_1', 'variant_2']

