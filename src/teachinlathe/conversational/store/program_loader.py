import json
import logging
import os
from typing import List

from teachinlathe.conversational.model.data_types import Program

log = logging.getLogger(__name__)


def load_programs_from_folder(folder_path: str) -> List[Program]:
    """Load only valid program JSON files from the given folder."""
    programs = []

    log.info("Loading programs from %s", folder_path)
    if not os.path.exists(folder_path):
        log.warning("Program folder %s does not exist", folder_path)
        return programs

    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    program = Program.from_dict(data)
                    program.filename = file_path
                    programs.append(program)
            except Exception as exc:
                log.warning("Could not load program %s: %s", filename, exc)

    return programs
