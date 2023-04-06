from types import FunctionType, MethodType
from . import Object, Function
from .utils import horizontal_line, boxed, tabled
from pathlib import PurePath
from typing import Tuple, TextIO


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
    file_fn_db: dict[str, list[Tuple[int, Function]]]

    def __init__(self) -> None:
        self.db = {}
        self.file_fn_db = {}

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

    def values(self):
        return self.db.values()

    def has_ob(self, ob: Object) -> bool:
        return ob in self.db.values()

    def file_fn_obs(self, filename: str):
        if filename in self.file_fn_db:
            return self.file_fn_db[filename]
        file_fn_obs = []
        for ob_pos, ob in self.db.items():
            if ob_pos.filename == filename and isinstance(ob, Function):
                file_fn_obs.append((ob_pos.start_line, ob))
        file_fn_obs = list(
            sorted(file_fn_obs, key=lambda x: x[0], reverse=True))
        self.file_fn_db[filename] = file_fn_obs
        return file_fn_obs

    def lookup_fn(self, fn: FunctionType | MethodType) -> Object | None:
        if not hasattr(fn, "__code__"):
            return None
        code = fn.__code__
        pos = Position(code.co_filename, code.co_firstlineno)
        if pos in self.db:
            return self.db[pos]
        else:
            return None


class KeywordDb:
    db: dict[Function, list[str]]

    def __init__(self) -> None:
        self.db = {}

    def append_possibility(self, fn: Function, poss: str) -> None:
        if fn not in self.db:
            self.db[fn] = []
        fn_list = self.db[fn]
        if poss not in fn_list:
            fn_list.append(poss)

    def __str__(self) -> str:
        return str(self.db)

    def items(self):
        return self.db.items()

    def print_fancy(self) -> None:
        if len(self.db) == 0:
            print(boxed('NO KEYWORDS FOUND'))
        else:
            print(boxed('POSSIBLE KEYWORDS'))
            for fn, kwds in self.items():
                print(f'  {fn}')
                fn_len = len('function') + 3 + \
                    len(str(fn.full_path())) + len(fn._format_args())
                print('  ' + horizontal_line(fn_len))
                print(tabled(kwds, spacing=8))
                print()

    def render_rst(self, file: TextIO) -> None:
        KeywordDb._render_section_header(
            file, 'Keyword Argument Functions', '=')
        file.write(
            f'There are {len(self.db)} functions for which valid keys were found.\n\n')
        for fn, kwds in self.items():
            fp = str(fn.full_path())
            KeywordDb._render_section_header(file, fp, '-')
            name = fn.full_path().components[-1]
            file.write(f'Signature: def {name}({fn._format_args()})\n\n')
            file.write('Valid keys:\n\n')
            for kwd in kwds:
                file.write(f'* {kwd}\n')
            file.write('\n')

    @staticmethod
    def _render_section_header(file: TextIO, header: str, sym: str) -> None:
        guard = sym * (len(header) + 1)
        file.write(f'{guard}\n')
        file.write(f'{header}\n')
        file.write(f'{guard}\n')
        file.write('\n')
