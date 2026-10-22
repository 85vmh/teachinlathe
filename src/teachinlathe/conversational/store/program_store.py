import json
import os


def sanitize_filename(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "."))
    safe = safe.strip().replace(" ", "_")
    return safe or "program"


def resolve_save_path(program, base_dir: str) -> str:
    derived_base_dir = os.path.abspath(base_dir or os.getcwd())
    filename = getattr(program, "filename", None)
    if filename and isinstance(filename, str) and filename.strip():
        candidate = os.path.abspath(filename)
        try:
            if os.path.commonpath((derived_base_dir, candidate)) == derived_base_dir:
                return candidate
        except ValueError:
            pass

    # Generated-program JSON lives in a separate export directory. When it is
    # opened for editing, keep saving to the original conversational file by
    # its stable program ID rather than to that disposable copy.
    program_id = getattr(program, "id", None)
    if program_id:
        id_path = os.path.join(derived_base_dir, f"{sanitize_filename(str(program_id))}.json")
        if os.path.isfile(id_path):
            return id_path

    base_name = None
    try:
        base_name = program.header.name
    except Exception:
        pass
    if not base_name:
        try:
            base_name = program.id
        except Exception:
            base_name = "program"

    base_name = sanitize_filename(str(base_name))
    if not base_name.lower().endswith(".json"):
        base_name += ".json"
    return os.path.join(derived_base_dir, base_name)


def save_program_to_disk(program, base_dir: str) -> str:
    data = program.to_dict() if hasattr(program, "to_dict") else None
    if not data:
        raise ValueError("Program serialization missing (to_dict).")

    filename = resolve_save_path(program, base_dir)
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    temporary = filename + ".tmp"
    try:
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=4)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, filename)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    program.filename = filename
    return filename
