"""Plans already worked out, kept by what went into them - the plan's inputs
only, so the preview's plan is the one the G-code is written from, and a value
the plan does not depend on (the feed, the spindle) does not plan again."""

from __future__ import annotations

import json
from collections import OrderedDict
from typing import Callable


def plan_key(**inputs) -> str:
    """A key from a plan's inputs, given as plain values: the same inputs, the
    same key, however the operation they came from was put together."""
    return json.dumps(inputs, sort_keys=True, default=str)


class PlanCache:
    """The plans last used, ``kept`` of them, by their keys (plan_key)."""

    def __init__(self, kept: int = 64):
        self.kept = kept
        self._plans: "OrderedDict[str, object]" = OrderedDict()

    def get(self, key: str, make: Callable[[], object]):
        """The plan kept for ``key``, else ``make()``'s, kept."""
        plan = self._plans.get(key)
        if plan is not None:
            self._plans.move_to_end(key)
            return plan
        plan = make()
        self._plans[key] = plan
        while len(self._plans) > self.kept:
            self._plans.popitem(last=False)
        return plan

    def forget(self, key: str):
        self._plans.pop(key, None)

    def clear(self):
        self._plans.clear()

    def __len__(self):
        return len(self._plans)

    def __contains__(self, key: str):
        return key in self._plans
