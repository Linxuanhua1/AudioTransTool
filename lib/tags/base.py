import mutagen,logging
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)

InternalTags = dict[str, set]


class MetaReader(ABC):
    def __init__(self, file_p: Path):
        self.file_p = file_p
        self.audio = mutagen.File(file_p)
        self._internal: InternalTags | None = None

    @property
    def internal(self) -> InternalTags:
        if self._internal is None:
            self._internal = self.read()
        return self._internal

    @abstractmethod
    def read(self) -> InternalTags:
        pass

    @staticmethod
    def copy_to(out_p: Path) -> None:
        pass

    @staticmethod
    def _merge(target: InternalTags, source: InternalTags) -> None:
        for key, values in source.items():
            target.setdefault(key, set()).update(values)


class MetaWriter(ABC):
    @abstractmethod
    def __init__(self, output_p: Path):
        pass

    @abstractmethod
    def write(self, internal: InternalTags) -> None:
        pass

