from abc import abstractmethod

class SavableOperationForm:
    @abstractmethod
    def hasUnsavedData(self) -> bool:
        """Returns True if the form contains unsaved changes"""
        raise NotImplementedError

    @abstractmethod
    def getOperation(self):
        """Returns the updated operation object"""
        raise NotImplementedError

    @abstractmethod
    def handleSave(self):
        raise NotImplementedError
