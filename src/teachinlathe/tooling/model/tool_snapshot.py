"""The Tool Library as it was at one moment, for code that cannot reach it.

ToolLibraryRepository lives in the application: it watches LinuxCNC and
writes the tool files, and there is one of it. The planning worker
(conversational/logic/plan_worker.py) generates G-code in a process of its
own, so it is handed a ToolSnapshot instead - the holders and what is clamped
in each, answering the two questions the G-code generators ask.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional

from .data_types import CuttingTool, ToolHolder


@dataclass(frozen=True)
class ToolSnapshot:
    holders: Dict[int, ToolHolder] = field(default_factory=dict)
    #: holder number -> the cutting tool mounted in it
    tools: Dict[int, CuttingTool] = field(default_factory=dict)

    @staticmethod
    def of(repository) -> "ToolSnapshot":
        holders = {h.tool_holder_id: h for h in repository.holders}
        tools = {number: tool for number in holders
                 if (tool := repository.tool_in(number)) is not None}
        return ToolSnapshot(holders, tools)

    def find_holder(self, tool_holder_id: Optional[int]) -> Optional[ToolHolder]:
        return self.holders.get(tool_holder_id)

    def tool_in(self, tool_holder_id: Optional[int]) -> Optional[CuttingTool]:
        return self.tools.get(tool_holder_id)
