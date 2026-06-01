import copy
import os
import re
import time
from datetime import datetime

from teachinlathe.conversational.data_types import Profiling, Program, Strategy
from teachinlathe.conversational.factories import make_default_operation, make_new_program


def renumber_operations(operations):
    for i, op in enumerate(operations):
        op.order = i + 1


def insert_default_operation(program, op_type: str, insert_index: int):
    new_op = make_default_operation(op_type)
    if op_type == "defineProfile":
        from teachinlathe.conversational.data_types import DefineProfile
        existing_ids = [op.profile_id for op in program.operations if isinstance(op, DefineProfile)]
        new_op.profile_id = (max(existing_ids) + 1) if existing_ids else 1
    ops = program.operations
    idx = max(0, min(insert_index, len(ops)))
    ops.insert(idx, new_op)
    renumber_operations(ops)
    return idx


def duplicate_operation(program, src_index: int, insert_index: int):
    ops = program.operations
    if src_index < 0 or src_index >= len(ops):
        raise IndexError(f"src_index {src_index} out of range")
    new_op = copy.deepcopy(ops[src_index])
    idx = max(0, min(insert_index, len(ops)))
    ops.insert(idx, new_op)
    renumber_operations(ops)
    return idx


def move_operation_up(program, index: int):
    if index <= 0:
        return None
    ops = program.operations
    ops.insert(index - 1, ops.pop(index))
    renumber_operations(ops)
    return index - 1


def move_operation_down(program, index: int):
    if index >= len(program.operations) - 1:
        return None
    ops = program.operations
    ops.insert(index + 1, ops.pop(index))
    renumber_operations(ops)
    return index + 1


def delete_operation(program, index: int):
    if not (0 <= index < len(program.operations)):
        return False
    program.operations.pop(index)
    renumber_operations(program.operations)
    return True


def add_profiling_finish(program, index: int):
    if not (0 <= index < len(program.operations)):
        raise IndexError(index)
    op = program.operations[index]
    if not isinstance(op, Profiling):
        raise TypeError("Selected operation is not Profiling")
    new_op = copy.deepcopy(op)
    new_op.profilingOptions.strategy = Strategy.FINISH
    insert_idx = index + 1
    program.operations.insert(insert_idx, new_op)
    renumber_operations(program.operations)
    return insert_idx


def delete_program_file(program):
    file_path = getattr(program, "filename", None)
    if file_path and os.path.exists(file_path):
        os.remove(file_path)


def make_timestamped_program_path(folder_path: str):
    while True:
        timestamp = datetime.now()
        file_stamp = timestamp.strftime("%d_%m_%Y_%H_%M_%S")
        filename = f"program_{file_stamp}.json"
        file_path = os.path.join(folder_path, filename)
        if not os.path.exists(file_path):
            return timestamp, filename, file_path
        time.sleep(0.01)


def next_duplicate_name(base_name: str, existing_names):
    stem = re.sub(r"\s+\(\d+\)$", "", base_name).rstrip()
    suffix = 1
    while True:
        candidate = f"{stem} ({suffix})"
        if candidate not in existing_names:
            return candidate
        suffix += 1


def duplicate_program(program, folder_path: str, existing_names):
    timestamp, filename, file_path = make_timestamped_program_path(folder_path)
    display_stamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    new_program = copy.deepcopy(program)
    new_program.id = os.path.splitext(filename)[0]
    new_program.filename = file_path
    new_program.header.name = next_duplicate_name(getattr(program.header, "name", "Program"), existing_names)
    new_program.header.created_date = display_stamp
    new_program.header.last_edit = display_stamp
    return new_program


def create_new_program(folder_path: str):
    return make_new_program(folder_path)
