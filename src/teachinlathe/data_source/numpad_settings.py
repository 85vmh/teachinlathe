"""Single source of truth for the SmartNumpad dialog configuration.

Loads ``configurations/numpad_settings.json`` and exposes, per ``settingName``:
the predefined values, description, limits and the persisted ``last_value``.

This module has **no** qtpyvcp dependency on purpose - the numpad config used
to live in the qtpyvcp settings (yml) and is now decoupled into plain JSON.

Only entries that declare a ``last_value`` field are persisted: when the user
picks a value for such a key it is written back to the JSON so the field is
repopulated with it next time (used for RPM / feed / CSS / max RPM).
"""

import json
import os
import threading

# configurations/ lives at the repository root, next to src/.
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..', '..', '..'))
DEFAULT_PATH = os.path.join(_REPO_ROOT, 'configurations', 'numpad_settings.json')


class NumpadSettings:
    """Loads / persists the numpad settings JSON. Use :meth:`instance`."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, file_path=DEFAULT_PATH):
        self._file_path = file_path
        self._lock = threading.Lock()
        self._data = {}
        self._load()

    def _load(self):
        try:
            with open(self._file_path, 'r') as fh:
                self._data = json.load(fh)
        except (OSError, ValueError):
            self._data = {}

    def get(self, key):
        """Return the raw config dict for *key*, or ``None``."""
        return self._data.get(str(key))

    def has(self, key):
        return str(key) in self._data

    def current_value(self, key):
        """Value the field should render with: ``last_value`` if present, else
        ``default_value`` (else ``None``)."""
        entry = self.get(key)
        if entry is None:
            return None
        if 'last_value' in entry:
            return entry['last_value']
        return entry.get('default_value')

    def set_last_value(self, key, value):
        """Persist *value* as ``last_value`` for *key* if that key opts in to
        persistence (i.e. already declares a ``last_value`` field)."""
        entry = self.get(key)
        if entry is None or 'last_value' not in entry:
            return
        entry['last_value'] = self._coerce(entry, value)
        self._save()

    @staticmethod
    def _coerce(entry, value):
        value_type = entry.get('value_type')
        if value_type == 'str':
            return str(value)
        try:
            number = float(value)
        except (TypeError, ValueError):
            return value
        if value_type == 'int':
            return int(round(number))
        return int(number) if number.is_integer() else number

    def _save(self):
        with self._lock:
            tmp_path = self._file_path + '.tmp'
            try:
                with open(tmp_path, 'w') as fh:
                    json.dump(self._data, fh, indent=2)
                os.replace(tmp_path, self._file_path)
            except OSError:
                pass
