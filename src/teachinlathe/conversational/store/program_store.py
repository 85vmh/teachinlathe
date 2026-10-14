import json
import os


def sanitize_filename(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in (" ", "-", "_", "."))
    safe = safe.strip().replace(" ", "_")
    return safe or "program"


def resolve_save_path(program, base_dir: str) -> str:
    filename = getattr(program, "filename", None)
    if filename and isinstance(filename, str) and filename.strip():
        return filename

    derived_base_dir = base_dir or os.getcwd()
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
    with open(filename, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
    program.filename = filename
    return filename
