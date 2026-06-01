"""Shared roughing context for OD and ID profile roughing.

RoughingContext captures the direction-dependent parameters that differ between
OD (exterior) and ID (interior) profiling. All roughing strategies (axial,
radial, diagonal) accept a RoughingContext so the same algorithm works for
both directions.

Key symmetry
------------
OD: x_safe = x_start + retract  (safe is outside / large X)
    x_limit = x_min + stock_x   (stop stock_x short of profile minimum)
    x_direction = -1             (X decreases toward profile)
    stock_x_sign = +1            (profile queries shift profile right to leave stock)

ID: x_safe = x_start - retract  (safe is toward bore centre / small X)
    x_limit = x_max - stock_x   (stop stock_x short of bore wall)
    x_direction = +1             (X increases toward profile)
    stock_x_sign = -1            (profile queries shift profile left to leave stock)

ProfileRoughing builds one shared roughing path from geo_x_shift / geo_z_shift
and clips it to X Start before dispatching to axial, radial, diagonal, and
contour strategies.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class RoughingContext:
    # ---- parameters from config ----
    x_start: float
    z_start: float
    doc: float
    retract: float
    stock_x: float
    stock_z: float
    optional_prefix: str

    # ---- direction-dependent (set by factory) ----
    x_safe: float       # OD: x_start + retract      ID: x_start - retract
    x_limit: float      # OD: x_min + stock_x         ID: x_max - stock_x
    x_direction: int    # OD: -1 (X decreases)        ID: +1 (X increases)
    stock_x_sign: int   # OD: +1                      ID: -1

    @property
    def geo_x_shift(self) -> float:
        """X shift applied to profile geometry queries (applies radial stock)."""
        return self.stock_x_sign * self.stock_x * 2

    @property
    def geo_z_shift(self) -> float:
        """Z shift applied to profile geometry queries (applies axial stock)."""
        return self.stock_z

    def clamp_cut_x(self, x: float) -> float:
        """Clamp a radial cut position so it never passes x_limit."""
        if self.x_direction < 0:   # OD: x decreases, don't go below x_limit
            return max(x, self.x_limit)
        return min(x, self.x_limit)  # ID: x increases, don't exceed x_limit

    def has_radial_range(self) -> bool:
        """Return True if there is material to remove between x_start and x_limit."""
        if self.x_direction < 0:
            return self.x_limit < self.x_start - 1e-9
        return self.x_limit > self.x_start + 1e-9


def make_od_context(config, x_min: float) -> RoughingContext:
    """Build a RoughingContext for OD (exterior) profile roughing."""
    doc = config.doc if config.doc > 0 else 0.5
    retract = abs(config.retract)
    return RoughingContext(
        x_start=config.x_start,
        z_start=config.z_start,
        doc=doc,
        retract=retract,
        stock_x=config.stock_x,
        stock_z=config.stock_z,
        optional_prefix=config.optional_prefix,
        x_safe=config.x_start + retract * 2,
        x_limit=x_min + config.stock_x * 2,
        x_direction=-1,
        stock_x_sign=1,
    )


def make_id_context(config, x_max: float) -> RoughingContext:
    """Build a RoughingContext for ID (interior / boring) profile roughing."""
    doc = config.doc if config.doc > 0 else 0.5
    retract = abs(config.retract)
    return RoughingContext(
        x_start=config.x_start,
        z_start=config.z_start,
        doc=doc,
        retract=retract,
        stock_x=config.stock_x,
        stock_z=config.stock_z,
        optional_prefix=config.optional_prefix,
        x_safe=config.x_start - retract * 2,
        x_limit=x_max - config.stock_x * 2,
        x_direction=1,
        stock_x_sign=-1,
    )
