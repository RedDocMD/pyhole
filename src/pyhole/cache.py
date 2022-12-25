from .db import Position


class FileCache:
    files: dict[str, list[str]]

    def __init__(self):
        self.files = {}

    def __getitem__(self, pos: Position) -> str:
        filename = pos.filename
        idx = pos.start_line - 1
        if filename not in self.files:
            self._open_file(filename)
        lines = self.files[filename]
        return lines[idx]

    def _open_file(self, filename):
        with open(filename) as f:
            lines = list(map(lambda x: x[:-1], f.readlines()))
            self.files[filename] = lines
