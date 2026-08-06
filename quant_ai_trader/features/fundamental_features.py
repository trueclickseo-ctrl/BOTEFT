"""Placeholder for point-in-time fundamentals in a later data-provider phase.

Fundamentals must be timestamped by their publication date to prevent look-ahead bias.
"""

import pandas as pd


def add_fundamental_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Return unchanged data until a point-in-time fundamental feed is configured."""
    return frame.copy()

