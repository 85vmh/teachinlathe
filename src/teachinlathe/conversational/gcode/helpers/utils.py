def get_float(source, key, default=0.0):
    """Extract a float value from a dict, returning default on any failure."""
    if not isinstance(source, dict):
        return float(default)
    try:
        return float(source.get(key, default))
    except Exception:
        return float(default)
