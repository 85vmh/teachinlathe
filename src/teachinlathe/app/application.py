"""What the app runs on: the HAL component and the repositories.

Built once at start-up, before any screen, in the order they need each
other - the status channel before what listens to it, the HAL component
before anything reads its pins - so that what has to happen from the first
moment does: the tool library loading the remembered tool again once the
machine is homed, say, whichever screen is showing.

The view models are not made here: they belong to the screens that bind
to them.
"""

from __future__ import annotations

import logging

from teachinlathe.core.command_repository import CommandRepository, command_repository
from teachinlathe.core.ini_repository import IniRepository, ini_repository
from teachinlathe.core.lathe_hal_component import TeachInLatheComponent
from teachinlathe.core.machine_repository import MachineRepository, machine_repository
from teachinlathe.core.status_repository import StatusRepository, status_repository
from teachinlathe.core.tool_library_repository import (
    ToolLibraryRepository, tool_library_repository,
)
from teachinlathe.machine.model.fixtures import LatheFixturesRepository

log = logging.getLogger(__name__)


class Application:
    def __init__(self) -> None:
        self.ini: IniRepository = ini_repository()
        self.status: StatusRepository = status_repository()
        self.commands: CommandRepository = command_repository()
        self.machine: MachineRepository = machine_repository()
        self.hal: TeachInLatheComponent = TeachInLatheComponent()
        self.tool_library: ToolLibraryRepository = tool_library_repository()
        self.fixtures: LatheFixturesRepository = LatheFixturesRepository()
        log.info("application ready")
