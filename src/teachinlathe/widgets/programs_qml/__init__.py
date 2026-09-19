__all__ = ["ProgramsController"]


def __getattr__(name):
    if name == "ProgramsController":
        from .ProgramsController import ProgramsController
        return ProgramsController
    raise AttributeError(name)
