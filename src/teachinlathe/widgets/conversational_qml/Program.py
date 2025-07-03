from PyQt5.QtCore import QObject, pyqtProperty


class Program(QObject):
    def __init__(self, programName, creationDate, lastEditDate):
        super().__init__()
        self._programName = programName
        self._creationDate = creationDate
        self._lastEditDate = lastEditDate

    @pyqtProperty(str)
    def programName(self):
        return self._programName

    @pyqtProperty(str)
    def creationDate(self):
        return self._creationDate

    @pyqtProperty(str)
    def lastEditDate(self):
        return self._lastEditDate
