"""Single source of truth for the SmartNumpad dialog configuration.

Loads ``configurations/numpad_settings.json`` and exposes, per ``settingName``:
the predefined values, description, limits and the persisted ``last_value``.

The numpad config used to live in the application settings (yml) and is now
decoupled into plain JSON, with no dependency on any settings framework.

Only entries that declare a ``last_value`` field are persisted: when the user
picks a value for such a key it is saved so the field is repopulated with it
next time (used for RPM / feed / CSS / max RPM). The JSON shipped in the
package is read-only once installed, so those values go to a small overlay in
``~/.config/teachinlathe/numpad_last_values.json`` and the shipped
``last_value`` only serves as the default until the user picks one.
"""

import json
import os
import threading

# configurations/ ships inside the teachinlathe package.
_THIS_DIR = os.path.dirname(os.path.realpath(__file__))
_PACKAGE_ROOT = os.path.abspath(os.path.join(_THIS_DIR, '..'))
DEFAULT_PATH = os.path.join(_PACKAGE_ROOT, 'configurations', 'numpad_settings.json')

_CONFIG_HOME = os.environ.get('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
LAST_VALUES_PATH = os.path.join(_CONFIG_HOME, 'teachinlathe', 'numpad_last_values.json')


class NumpadSettings:
    """Loads / persists the numpad settings JSON. Use :meth:`instance`."""

    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, file_path=DEFAULT_PATH, last_values_path=LAST_VALUES_PATH):
        self._file_path = file_path
        self._last_values_path = last_values_path
        self._lock = threading.Lock()
        self._data = {}
        self._load()

    def _load(self):
        try:
            with open(self._file_path, 'r') as fh:
                self._data = json.load(fh)
        except (OSError, ValueError):
            self._data = {}

        try:
            with open(self._last_values_path, 'r') as fh:
                last_values = json.load(fh)
        except (OSError, ValueError):
            return
        if not isinstance(last_values, dict):
            return
        for key, value in last_values.items():
            entry = self._data.get(key)
            # Keys the shipped JSON dropped or stopped persisting are ignored.
            if entry is not None and 'last_value' in entry:
                entry['last_value'] = value

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
        last_values = {key: entry['last_value']
                       for key, entry in self._data.items()
                       if 'last_value' in entry}
        with self._lock:
            tmp_path = self._last_values_path + '.tmp'
            try:
                os.makedirs(os.path.dirname(self._last_values_path), exist_ok=True)
                with open(tmp_path, 'w') as fh:
                    json.dump(last_values, fh, indent=2)
                os.replace(tmp_path, self._last_values_path)
            except OSError:
                pass
