from abc import ABC, abstractmethod


class Command(ABC):
    """Abstract base class for all commands that modify the project."""
    
    def __init__(self, description=""):
        self.description = description

    @abstractmethod
    def execute(self):
        """Execute the command and return True if successful, False otherwise."""
        pass

    @abstractmethod
    def undo(self):
        """Undo the command and return True if successful, False otherwise."""
        pass

    def __str__(self):
        return self.description


# --- Mind Map Node Commands ---
