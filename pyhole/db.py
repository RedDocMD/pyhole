from .object import Object
from pathlib import PurePath


class Position:
    filename: str
    start_line: int

    def __init__(self, filename: PurePath | str, start_line: int) -> None:
        if isinstance(filename, PurePath):
            self.filename = str(filename)
        else:
            self.filename = filename
        self.start_line = start_line

    def __str__(self) -> str:
        return f"{self.filename}:{self.start_line}"

    def __repr__(self):
        return str(self)

    def __hash__(self):
        return hash((self.filename, self.start_line))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (
                self.filename == other.filename and self.start_line == other.start_line
            )
        raise NotImplementedError

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        raise NotImplementedError



class ObjectDb:
    db: dict[Position, Object]

    def __init__(self) -> None:
        self.db = {}

    def __setitem__(self, pos: Position, ob: Object) -> None:
        if pos in self.db:
            raise RuntimeError(f"{pos} already exists in db")
        self.db[pos] = ob

    def __getitem__(self, pos: Position) -> Object:
        return self.db[pos]

    def __len__(self) -> int:
        return len(self.db)

    def __iter__(self):
        return self.db.__iter__()

    def items(self):
        return self.db.items()
