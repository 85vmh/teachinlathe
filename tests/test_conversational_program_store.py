import json
from types import SimpleNamespace

from teachinlathe.conversational.store.program_store import save_program_to_disk


class FakeProgram:
    def __init__(self, program_id, name, filename, payload):
        self.id = program_id
        self.header = SimpleNamespace(name=name)
        self.filename = filename
        self.payload = payload

    def to_dict(self):
        return self.payload


def test_save_from_generated_json_copy_updates_canonical_program(tmp_path):
    programs = tmp_path / "conversational"
    exports = tmp_path / "generated" / "json"
    programs.mkdir()
    exports.mkdir(parents=True)
    canonical = programs / "program_123.json"
    copy = exports / "Shaft.json"
    canonical.write_text('{"version": "old"}', encoding="utf-8")
    copy.write_text('{"version": "generated copy"}', encoding="utf-8")
    program = FakeProgram(
        "program_123", "Renamed shaft", str(copy), {"version": "edited"}
    )

    saved = save_program_to_disk(program, str(programs))

    assert saved == str(canonical)
    assert program.filename == str(canonical)
    assert json.loads(canonical.read_text(encoding="utf-8")) == {"version": "edited"}
    assert json.loads(copy.read_text(encoding="utf-8")) == {"version": "generated copy"}


def test_external_program_without_canonical_id_saves_into_program_folder(tmp_path):
    programs = tmp_path / "conversational"
    programs.mkdir()
    external = tmp_path / "imported.json"
    program = FakeProgram(
        "imported_1", "A new program", str(external), {"version": "edited"}
    )

    saved = save_program_to_disk(program, str(programs))

    assert saved == str(programs / "A_new_program.json")
    assert json.loads((programs / "A_new_program.json").read_text(encoding="utf-8")) == {
        "version": "edited"
    }

