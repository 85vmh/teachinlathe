# Number of decimal places used when formatting coordinate and dimensional
# values in generated G-code.
#   3 = metric (mm)
#   4 = imperial (inches)
COORD_DECIMALS = 3


def fmt(v):
    """Format a coordinate or dimensional value for G-code output."""
    return f"{float(v):.{COORD_DECIMALS}f}"