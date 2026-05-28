import pandas as pd
import numpy as np
import pytest


@pytest.fixture
def sample_ohlcv():
    """250 rows of synthetic OHLCV data for indicator tests."""
    rng = np.random.default_rng(42)
    n = 250
    close = 2000 + np.cumsum(rng.normal(0, 5, n))
    high = close + rng.uniform(1, 10, n)
    low = close - rng.uniform(1, 10, n)
    open_ = close + rng.normal(0, 3, n)
    volume = rng.integers(100, 1000, n).astype(float)
    df = pd.DataFrame({'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume})
    return df
