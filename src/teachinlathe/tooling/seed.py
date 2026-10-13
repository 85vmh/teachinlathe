"""What the tool library starts with on a machine that has none yet.

A few tools of every kind, and holders in each state a holder can be in:
empty, holding a tool that has not been touched off, and ready.
"""

from __future__ import annotations

from typing import List

from teachinlathe.tooling.data_types import (
    BladeTool, BoringTool, CuttingTool, DrillingTool, HolderOrientation,
    InsertSpec, ReamingTool, SolidBody, SpindleDirection, TappingTool,
    ThreadingTool, ToolHolder, TurningTool, TwistDirection, ZOffsetPlace,
)


def seed_cutting_tools() -> List[CuttingTool]:
    m4 = SpindleDirection.M4
    m3 = SpindleDirection.M3        # right-hand drills and taps cut with M3
    return [
        TurningTool(cutting_tool_id=1, insert=InsertSpec("ccmt", "06", "02"),
                    orientation=2, front_angle=95, back_angle=5, spindle_direction=m4),
        TurningTool(cutting_tool_id=2, insert=InsertSpec("dcmt", "11", "04"),
                    orientation=2, front_angle=93, back_angle=32, spindle_direction=m4),
        TurningTool(cutting_tool_id=3, insert=InsertSpec("vbmt", "16", "04"),
                    orientation=6, front_angle=72.5, back_angle=72.5, spindle_direction=m4),
        BoringTool(cutting_tool_id=4, insert=InsertSpec("ccmt", "06", "02"),
                   solid_body=SolidBody(tip_angle=50, diameter=5, max_radial_undercut=3),
                   orientation=6, front_angle=5, back_angle=5, spindle_direction=m4),
        BoringTool(cutting_tool_id=5, insert=InsertSpec("ccmt", "09", "04"),
                   solid_body=SolidBody(tip_angle=50, diameter=10, max_radial_undercut=6),
                   orientation=6, front_angle=5, back_angle=5, spindle_direction=m4),
        BladeTool(cutting_tool_id=6, blade_width=3, left_radius=0.5, right_radius=0.5,
                  orientation=6, spindle_direction=m4),
        BladeTool(cutting_tool_id=7, blade_width=2, left_radius=0.2, right_radius=0.2,
                  orientation=6, spindle_direction=m4),
        ThreadingTool(cutting_tool_id=8, insert=InsertSpec("ER", "16", "02"),
                      orientation=6, spindle_direction=m4),
        ThreadingTool(cutting_tool_id=9, insert=InsertSpec("IR", "16", "02"),
                      orientation=8, spindle_direction=m4),
        DrillingTool(cutting_tool_id=10, diameter=10, tip_angle=118,
                     twist_direction=TwistDirection.RIGHT_HAND, spindle_direction=m3),
        DrillingTool(cutting_tool_id=11, diameter=6.8, tip_angle=118,
                     twist_direction=TwistDirection.RIGHT_HAND, spindle_direction=m3),
        TappingTool(cutting_tool_id=12, diameter=10, pitch=1.5,
                    twist_direction=TwistDirection.RIGHT_HAND, spindle_direction=m3),
        ReamingTool(cutting_tool_id=13, diameter=10, spindle_direction=m4),
    ]


def seed_tool_holders() -> List[ToolHolder]:
    return [
        ToolHolder(1, HolderOrientation.RADIAL, cutting_tool_id=1,
                   x_offset=123.123, z_offset=45.678),
        ToolHolder(2, HolderOrientation.RADIAL, cutting_tool_id=2),
        ToolHolder(3, HolderOrientation.AXIAL, cutting_tool_id=4,
                   x_offset=98.765, z_offset=60.5),
        ToolHolder(4, HolderOrientation.RADIAL, cutting_tool_id=6,
                   x_offset=110.0, z_offset=52.25, z_offset_place=ZOffsetPlace.LEFT),
        ToolHolder(5, HolderOrientation.AXIAL),
        ToolHolder(6, HolderOrientation.RADIAL, cutting_tool_id=8,
                   x_offset=115.4, z_offset=48.0),
    ]
