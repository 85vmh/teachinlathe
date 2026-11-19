# Number of decimal places used when formatting coordinate and dimensional
# values in generated G-code.
#   3 = metric (mm)
#   4 = imperial (inches)
COORD_DECIMALS = 3


def fmt(v):
    """Format a coordinate or dimensional value for G-code output."""
    return f"{float(v):.{COORD_DECIMALS}f}"

#: How far an operation retracts off each cut, as a part of its depth of cut
#: (Ap): by operation type - the ``type`` of its JSON.
RETRACT_OF_AP = {
    "profileRoughing": 1 / 2,
    "turning": 1 / 2,
    "facing": 1 / 2,
}


def retract_of(op_type: str, ap: float) -> float:
    """The retract off each cut of an operation of ``op_type`` that cuts
    ``ap`` deep: its part of Ap (RETRACT_OF_AP)."""
    return float(ap) * RETRACT_OF_AP[op_type]
