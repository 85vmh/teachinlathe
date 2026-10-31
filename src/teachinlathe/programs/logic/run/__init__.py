"""A program run behind one interface (ProgramRunSource): the machine
running it, or a simulation of it."""

from teachinlathe.programs.logic.run.machine_run_source import MachineRunSource
from teachinlathe.programs.logic.run.run_source import ProgramRunSource
from teachinlathe.programs.logic.run.simulated_run_source import SimulatedRunSource

__all__ = ["MachineRunSource", "ProgramRunSource", "SimulatedRunSource"]
