"""Where the backplot's picture comes from - the machine or a simulated run -
behind one interface: a PlotSource's status, trail and material left."""

from teachinlathe.ui.tabs.programs.backplot.plot_source.source import MachineSource, SimulationSource
from teachinlathe.ui.tabs.programs.backplot.plot_source.trail import COLOR_NAMES

__all__ = ["COLOR_NAMES", "MachineSource", "SimulationSource"]
