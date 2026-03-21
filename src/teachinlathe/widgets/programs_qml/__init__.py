__all__ = ["ProgramsQml"]


def __getattr__(name):
    if name == "ProgramsQml":
        from .ProgramsQml import ProgramsQml
        return ProgramsQml
    raise AttributeError(name)
