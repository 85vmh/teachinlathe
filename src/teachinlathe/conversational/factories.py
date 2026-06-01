import os
from datetime import datetime

from teachinlathe.conversational.data_types import (
    BlendType,
    ChangeTool,
    CoordinateType,
    CuttingParameters,
    Drilling,
    DrillingParameters,
    EdgeBreak,
    Facing,
    GeometryParameters,
    Header,
    Knurling,
    KnurlingCuttingParameters,
    KnurlingGeometryParameters,
    M1Parameters,
    MoveSequence,
    PositionAt,
    PositionDetails,
    PredefinedPosition,
    Parting,
    PartingParameters,
    PassType,
    ProfileContour,
    ProfileContourStrategy,
    ProfileRoughing,
    ProfileRoughingStrategy,
    Profiling,
    ProfilingOptions,
    ProfilingParameters,
    ProfilingType,
    Program,
    StockToLeave,
    SpindleMode,
    SpindleParameters,
    StartPoint,
    Strategy,
    Tapping,
    TappingParameters,
    ThreadLocation,
    Threading,
    Workpiece,
    DefineProfile,
)


def make_default_operation(op_type: str, order: int = 1):
    spindle_rpm = SpindleParameters(direction=1, mode=SpindleMode.RPM, rpm_value=1000)
    m1_default = M1Parameters(include_m1=False, inspect_position=PredefinedPosition.G28, stop_spindle=False)

    if op_type == "changeTool":
        return ChangeTool(
            order=order,
            type=op_type,
            generate_gcode=True,
            is_optional_block=False,
            tool_no=1,
            tool_orientation=1,
            back_angle=0,
            front_angle=0,
            toolchange_position=PredefinedPosition.G28,
        )
    if op_type == "positionAt":
        return PositionAt(
            order=order,
            type=op_type,
            generate_gcode=True,
            is_optional_block=False,
            position_details=PositionDetails(
                x_pos=0.0,
                z_pos=0.0,
                coordinate_type=CoordinateType.ABSOLUTE,
                move_sequence=MoveSequence.XZ,
            ),
        )
    if op_type == "facing":
        return Facing(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            cuttingParameters=CuttingParameters(feedRate=0.1, doc=0.5, retract=1.0),
            geometryParameters=GeometryParameters(xStart=0.0, zStart=0.0, xEnd=0.0, zEnd=0.0),
            m1Parameters=m1_default,
            zEndBecomesNewZ0=False,
        )
    if op_type == "knurling":
        return Knurling(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            cuttingParameters=KnurlingCuttingParameters(doc=0.5, retract=1.0, groovesCount=1),
            geometryParameters=KnurlingGeometryParameters(zStart=0.0, zEnd=0.0, xStart=0.0),
            m1Parameters=M1Parameters(include_m1=True, inspect_position=PredefinedPosition.G28, stop_spindle=False),
        )
    if op_type == "profiling":
        return Profiling(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            cuttingParameters=CuttingParameters(feedRate=0.1, doc=0.5, retract=1.0),
            profilingParameters=ProfilingParameters(profile_id=1, xStart=0.0, zStart=0.0),
            profilingOptions=ProfilingOptions(
                strategy=Strategy.ROUGH, stockToLeaveX=0.0, stockToLeaveZ=0.0, finishPasses=1, finishSpringPasses=0
            ),
        )
    if op_type == "profileRoughing":
        return ProfileRoughing(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            cuttingParameters=CuttingParameters(feedRate=0.1, doc=0.5, retract=1.0),
            profilingParameters=ProfilingParameters(profile_id=1, xStart=0.0, zStart=0.0),
            profileRoughingStrategy=ProfileRoughingStrategy(
                profiling_type=ProfilingType.OD,
                pass_type=PassType.AXIAL,
            ),
            stockToLeave=StockToLeave(stockToLeaveX=0.0, stockToLeaveZ=0.0),
            m1Parameters=M1Parameters(include_m1=False, inspect_position=PredefinedPosition.G28, stop_spindle=False),
        )
    if op_type == "profileContour":
        return ProfileContour(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            cuttingParameters=CuttingParameters(feedRate=0.1, doc=0.5, retract=1.0),
            profilingParameters=ProfilingParameters(profile_id=1, xStart=0.0, zStart=0.0),
            profileContourStrategy=ProfileContourStrategy(profiling_type=ProfilingType.OD),
            stockToLeave=StockToLeave(stockToLeaveX=0.0, stockToLeaveZ=0.0),
            stockToLeaveEnabled=False,
        )
    if op_type == "threading":
        return Threading(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=SpindleParameters(direction=1, mode=SpindleMode.RPM, rpm_value=500),
            location=ThreadLocation.OD, thread_type="metric", pitch=1.0, starts=1,
            major_diameter=0.0, minor_diameter=0.0, z_start=0.0, z_end=0.0,
            initial_doc=0.3, retract=1.0, spring_passes=0, depth_degression=1.0, taper_type=0, compound_angle=0.0,
        )
    if op_type == "drilling":
        return Drilling(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=spindle_rpm,
            drillingParameters=DrillingParameters(zStart=0.0, zEnd=0.0, zRetract=5.0, peckDepth=3.0, feedRate=0.05),
            m1Parameters=m1_default,
        )
    if op_type == "tapping":
        return Tapping(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=SpindleParameters(direction=1, mode=SpindleMode.RPM, rpm_value=500),
            tappingParameters=TappingParameters(zStart=0.0, zEnd=0.0, zRetract=5.0, peckDepth=0.0, pitch=1.0),
            m1Parameters=m1_default,
        )
    if op_type == "parting":
        return Parting(
            order=order, type=op_type, generate_gcode=True, is_optional_block=False,
            spindleParameters=SpindleParameters(direction=1, mode=SpindleMode.RPM, rpm_value=500),
            partingParameters=PartingParameters(
                xStart=0.0, xEnd=0.0, zPos=0.0, first_feed_rate=0.05, second_feed_rate=0.02, second_feed_x_pos=5.0, x_clearance=1.0
            ),
            edgeBreak=EdgeBreak(blend_type=BlendType.NONE, chamfer_width=0.0, fillet_radius=0.0),
        )
    if op_type == "defineProfile":
        return DefineProfile(
            order=order, type=op_type, generate_gcode=False, is_optional_block=False,
            profile_id=1, profile_type=ProfilingType.OD, profile_primitives=[]
        )
    raise ValueError(f"Unknown operation type: {op_type!r}")


def make_new_program(folder_path: str):
    timestamp = datetime.now()
    file_stamp = timestamp.strftime("%d_%m_%Y_%H_%M_%S")
    display_stamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    filename = f"program_{file_stamp}.json"
    file_path = os.path.join(folder_path, filename)
    program_name = f"Program {file_stamp}"
    header = Header(
        name=program_name,
        created_date=display_stamp,
        last_edit=display_stamp,
        datum=1,
        units="mm",
        workpiece=Workpiece(material="", external_diameter=0.0, internal_diameter=0.0, stickout_length=0.0),
    )
    return Program(id=os.path.splitext(filename)[0], header=header, operations=[], filename=file_path)
