import os
import json

import os
import json
from typing import List

from teachinlathe.conversational.data_types import Program


def load_programs_from_folder(folder_path: str) -> List[Program]:
    """Load all programs from JSON files in the given folder."""
    programs = []

    print(f"Loading programs from {folder_path}")
    if not os.path.exists(folder_path):
        print(f"Warning: Folder {folder_path} does not exist.")
        return programs

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            file_path = os.path.join(folder_path, filename)
            print(f"---Loading program from {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    program = Program.from_dict(data)
                    programs.append(program)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error loading {filename}: {e}")

    return programs
