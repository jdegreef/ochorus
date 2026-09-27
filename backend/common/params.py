"""Coercing untrusted request values."""


def clamp_int(value, default=0, low=0, high=None) -> int:
    """``value`` as an int within [low, high], or ``default`` if it isn't one.

    Out-of-range values are clamped, not rejected, and a bound is what keeps a
    huge number from reaching the database as an out-of-range integer (a 500).
    """
    try:
        n = max(low, int(value))
    except (TypeError, ValueError):
        return default
    return min(high, n) if high is not None else n
