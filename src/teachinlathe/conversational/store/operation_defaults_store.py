"""The last values a new operation starts with (model.operation_defaults),
kept in a JSON file in the machine's config directory: one patch per type of
operation, ``{"facing": {"speeds_and_feeds": {...}, ...}, ...}``.

With no path it keeps them in memory only. A file that cannot be read is
taken for none, and logged."""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

OPERATION_DEFAULTS_FILE = "teachinlathe_operation_defaults.json"


class OperationDefaultsStore:
    def __init__(self, path: Optional[str] = None) -> None:
        self._path = path
        self._patches: Dict[str, Dict[str, Any]] = self._load()

    def patch_for(self, key: Optional[str]) -> Dict[str, Any]:
        """What a new operation kept under ``key`` starts with; {} for nothing."""
        return copy.deepcopy(self._patches.get(key, {})) if key else {}

    def remember(self, key: Optional[str], patch: Dict[str, Any]) -> None:
        """``patch`` for what ``key`` starts with now, written when it is new."""
        if not key or not patch or patch == self._patches.get(key):
            return
        self._patches[key] = copy.deepcopy(patch)
        self._save()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self._path:
            return {}
        try:
            with open(self._path, encoding="utf-8") as fh:
                stored = json.load(fh)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            log.warning("could not read the operation defaults %s; starting without them",
                        self._path, exc_info=True)
            return {}
        if not isinstance(stored, dict):
            log.warning("operation defaults %s do not hold an object; ignoring them", self._path)
            return {}
        return {key: value for key, value in stored.items() if isinstance(value, dict)}

    def _save(self) -> None:
        if not self._path:
            return
        try:
            tmp = self._path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump(self._patches, fh, indent=2, sort_keys=True)
            os.replace(tmp, self._path)
        except OSError:
            log.warning("could not write the operation defaults %s", self._path, exc_info=True)
