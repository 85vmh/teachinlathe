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
from teachinlathe.events.logic.events_use_case import EventsUseCase, events_use_case
from teachinlathe.machine.model.fixtures import LatheFixturesRepository

log = logging.getLogger(__name__)


class Application:
    def __init__(self) -> None:
        self.ini: IniRepository = ini_repository()
        self.status: StatusRepository = status_repository()
        # The Events list, and behind it the error channel's only reader: from
        # the start, so that no message is lost before the first screen.
        self.events: EventsUseCase = events_use_case()
        self.commands: CommandRepository = command_repository()
        self.machine: MachineRepository = machine_repository()
        self.hal: TeachInLatheComponent = TeachInLatheComponent()
        self.tool_library: ToolLibraryRepository = tool_library_repository()
        self.fixtures: LatheFixturesRepository = LatheFixturesRepository()
        self.diagnostics = self._make_diagnostics()
        log.info("application ready")

    @staticmethod
    def _make_diagnostics():
        """The diagnostics service, in the mode the setting - or, for this start,
        TEACHINLATHE_PROFILING - says; stopped as the application quits."""
        from PyQt6.QtCore import QCoreApplication

        from teachinlathe.core.settings_repository import SettingSpec, settings_repository
        from teachinlathe.diagnostics.logic.diagnostics_service import DiagnosticsService
        from teachinlathe.diagnostics.model.modes import SETTING, ProfilingMode, mode_at_start

        settings = settings_repository()
        settings.declare(SETTING, SettingSpec(default=ProfilingMode.OFF.value, value_type=str,
                                              description="Profiling: off, basic or detailed"))
        service = DiagnosticsService(mode_at_start(settings.get(SETTING)))
        app = QCoreApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(service.shutdown)
        return service
