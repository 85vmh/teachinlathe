"""ViewModel backing the QML SmartNumpadDialog.

Bridges the plain-data :class:`NumpadSettings` to QML: given a ``settingName``
it reports whether predefined values exist, the title, the options and limits,
and (only for the manual tab) persists the chosen value as ``last_value``.

The manual tab uses an instance with ``persist=True`` so picking a value is
remembered; the conversational tab uses ``persist=False`` so it only reads the
predefined values and never writes ``last_value``.
"""

from PyQt5.QtCore import QObject, pyqtSlot

from teachinlathe.data_source.numpad_settings import NumpadSettings


class NumpadDialogViewModel(QObject):
    # Virtual keys whose options are the de-duplicated union of several JSON
    # entries. Used by the conversational spindle fields, which are not tied to
    # a gear and so combine both gears' value lists.
    MERGED_KEYS = {
        "spindle.rpm": ("spindle.rpm_1", "spindle.rpm_2"),
        "spindle.max_rpm": ("spindle.css_max_rpm_1", "spindle.css_max_rpm_2"),
    }
    MERGED_DESCRIPTIONS = {
        "spindle.rpm": "Enter spindle target RPM",
        "spindle.max_rpm": "Enter spindle Max RPM",
    }

    def __init__(self, parent=None, persist=True):
        super().__init__(parent)
        self._settings = NumpadSettings.instance()
        self._persist = persist

    @pyqtSlot(str, result='QVariantMap')
    def configFor(self, setting_name):
        """Return everything QML needs to render the dialog for *setting_name*."""
        if setting_name in self.MERGED_KEYS:
            return self._merged_config(setting_name)

        entry = self._settings.get(setting_name)
        if entry is None:
            return {
                "hasConfig": False,
                "hasOptions": False,
                "options": [],
                "description": "",
                "valueType": "",
                "currentValue": None,
            }

        options = entry.get("options") or []
        return {
            "hasConfig": True,
            "hasOptions": isinstance(options, list) and len(options) > 0,
            "options": list(options),
            "description": entry.get("description", "") or "",
            "minValue": entry.get("min_value"),
            "maxValue": entry.get("max_value"),
            "defaultValue": entry.get("default_value"),
            "currentValue": self._settings.current_value(setting_name),
            "valueType": entry.get("value_type", "") or "",
        }

    def _merged_config(self, setting_name):
        merged = set()
        for key in self.MERGED_KEYS[setting_name]:
            entry = self._settings.get(key)
            if entry:
                for opt in entry.get("options") or []:
                    merged.add(opt)
        options = sorted(merged)
        return {
            "hasConfig": True,
            "hasOptions": len(options) > 0,
            "options": options,
            "description": self.MERGED_DESCRIPTIONS.get(setting_name, ""),
            "minValue": options[0] if options else None,
            "maxValue": options[-1] if options else None,
            "defaultValue": None,
            "currentValue": None,
            "valueType": "",
        }

    @pyqtSlot(str, "QVariant")
    def commitValue(self, setting_name, value):
        """Persist *value* as the key's ``last_value`` (manual tab only)."""
        if not self._persist:
            return
        self._settings.set_last_value(setting_name, value)
