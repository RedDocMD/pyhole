from object import Object
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


class ObjectDb:
    db: dict[Position, Object]

    def __init__(self) -> None:
        self.db = {}

    def insert(self, pos: Position, ob: Object) -> None:
        if pos in self.db:
            raise RuntimeError(f"{pos} already exists in db")
        self.db[pos] = ob

    def get(self, pos: Position) -> Object:
        return self.db[pos]
