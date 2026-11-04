from teachinlathe.conversational.model.data_types import MoveSequence, PositionAt

from ..toolpath import GcodeEmitter


def position_at_toolpath(op: PositionAt, path: GcodeEmitter, program=None):
    """``op``'s G-code, and its moves, onto ``path``: a rapid to the position,
    X and Z in the order it says - or both at once."""
    details = op.position_details

    if details.stop_spindle_before_positioning:
        path.code_comment("M5", "stop the spindle")
        path.blank()

    path.code_comment("G90", "absolute distance mode")

    if details.move_sequence == MoveSequence.XZ:
        path.rapid(x=details.x_pos)
        path.rapid(z=details.z_pos)
    elif details.move_sequence == MoveSequence.ZX:
        path.rapid(z=details.z_pos)
        path.rapid(x=details.x_pos)
    else:
        path.rapid(details.x_pos, details.z_pos)

    if details.include_m0:
        path.blank()
        path.code_comment("M0", "pause program")


def generate_position_at_gcode(op: PositionAt):
    """``op``'s G-code on its own."""
    path = GcodeEmitter(op.is_optional_block)
    position_at_toolpath(op, path)
    return path.lines
