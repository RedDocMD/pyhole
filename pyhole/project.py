from pathlib import PurePath, Path
from object import ObjectCreator, Object, Module, SourceSpan, Function
from db import ObjectDb, Position
from typing import Tuple
import re
import ast


pyfile_re = re.compile(r"^.*\.py$")


class DirChildren:
    init: PurePath | None
    files: list[PurePath]
    dirs: list[PurePath]

    def __init__(
        self, init: PurePath | None, files: list[PurePath], dirs: list[PurePath]
    ) -> None:
        self.init = init
        self.files = files
        self.dirs = dirs


# Children of a directory, with files at first and directory at last
# Files must end with .py, and the __init__.py file comes at first.
def dir_children(path: PurePath) -> DirChildren:
    path = Path(path)
    files: list[PurePath] = []
    dirs: list[PurePath] = []
    init: PurePath | None = None
    for child in path.iterdir():
        if child.is_dir():
            dirs.append(child)
        elif child.is_file():
            name = child.name
            if not pyfile_re.fullmatch(name):
                continue
            if name == "__init__.py":
                init = child
            else:
                files.append(child)
    return DirChildren(init, files, dirs)


class InitPyNotFound(Exception):
    pass


def mod_from_file(path: PurePath) -> Module:
    with open(path) as f:
        code = f.read()
        line_cnt = len(code.split("\n"))
        obc = ObjectCreator(path, line_cnt)
        tree = ast.parse(code, str(path))
        assert isinstance(tree, ast.Module)
        return obc.visit(tree)


def position_from_source_span(span: SourceSpan) -> Position:
    return Position(span.filename, span.start_line)


# Represents a project on which we want to run
# our algorithm
class Project:
    root: PurePath
    db: ObjectDb
    kw_fns: ObjectDb

    def __init__(self, root: PurePath) -> None:
        self.root = root
        self.db = ObjectDb()  # All objects
        self.kw_fns = ObjectDb()  # Functions with keyword arguments

        self._populate_db()
        self._find_kw_fns()

    def _find_kw_fns(self):
        for pos, ob in self.ob.items():
            if isinstance(ob, Function) and ob.has_kwargs_dict():
                self.kw_fns[pos] = ob

    def _populate_db(self):
        par_st: list[Object | None] = [None]
        self._populate_db_intern(par_st, self.root)

    def _populate_db_intern(self, par_st: list[Object], directory: PurePath):
        par = par_st[-1]
        new_mod, new_dirs = self._populate_from_directory(directory, par)
        par.append(new_mod)
        for new_dir in new_dirs:
            self._populate_db_intern(par_st, new_dir)
        par.pop()

    # Populate db using directory as root
    # Returns list of sub-directories
    def _populate_from_directory(
        self, directory: PurePath, par: Object | None
    ) -> Tuple[Module, list[PurePath]]:
        drc = dir_children(directory)
        if drc.init is None:
            raise InitPyNotFound("__init__.py not found in {}".format(directory))

        # Find main module of this directory
        main_mod = mod_from_file(drc.init)
        main_mod.parent = par
        self._populate_from_object(main_mod)

        # Then do the direct sub-modules
        for file in drc.files:
            mod = mod_from_file(file)
            mod.parent = main_mod
            self._populate_from_object(mod)

        return (main_mod, drc.dirs)

    def _populate_from_object(self, ob: Object):
        pos = position_from_source_span(ob.source_span)
        self.db[pos] = ob
        for child in ob.children:
            self._populate_from_object(child)
