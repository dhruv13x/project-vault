from abc import ABC, abstractmethod
from typing import List, Dict, Optional, IO

class BaseDatabaseDriver(ABC):
    """
    Abstract base class for database drivers.
    All drivers must implement backup (dump) and restore methods using streaming pipes.
    """

    @abstractmethod
    def get_backup_command(self, config: Dict) -> List[str]:
        """
        Returns the command line arguments to run the database dump.
        The output should be streamed to stdout.
        """
        pass

    @abstractmethod
    def get_restore_command(self, config: Dict) -> List[str]:
        """
        Returns the command line arguments to restore the database.
        The input should be streamed from stdin.
        """
        pass

    @abstractmethod
    def get_verification_command(self, config: Dict) -> List[str]:
        """
        Returns the command to verify connection/existence of the database.
        """
        pass

    @abstractmethod
    def get_drop_command(self, config: Dict) -> List[str]:
        """
        Returns the command to drop the database/schema if force is requested.
        """
        pass
