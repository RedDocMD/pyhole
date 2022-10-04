from pathlib import PurePath, Path
from types import NoneType
from .object import ObjectCreator, Object, Module, SourceSpan, Function
from .db import ObjectDb, Position
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
        if child.is_dir() and child.name != "__pycache__":
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


def mod_from_file(path: PurePath | str, mod_name: str | NoneType = None) -> Module:
    if isinstance(path, str):
        path = PurePath(path)
    with open(path) as f:
        code = f.read()
        line_cnt = len(code.split("\n"))
        obc = ObjectCreator(path, line_cnt, mod_name)
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
    root_ob: Object

    def __init__(self, root: PurePath) -> None:
        self.root = root
        self.db = ObjectDb()  # All objects
        self.kw_fns = ObjectDb()  # Functions with keyword arguments
        self.root_ob = None

        self._populate_db()
        self._find_kw_fns()

    def _find_kw_fns(self) -> None:
        for pos, ob in self.db.items():
            if isinstance(ob, Function) and ob.has_kwargs_dict():
                self.kw_fns[pos] = ob

    def _populate_db(self) -> None:
        par_st: list[Object | None] = [None]
        self._populate_db_intern(par_st, self.root)

    def _populate_db_intern(self, par_st: list[Object], directory: PurePath) -> None:
        par = par_st[-1]
        new_mod, new_dirs = self._populate_from_directory(directory, par)
        if self.root_ob is None:
            self.root_ob = new_mod
        if par:
            par.append(new_mod)
        for new_dir in new_dirs:
            self._populate_db_intern(par_st, new_dir)
        par_st.pop()

    # Populate db using directory as root
    # Returns list of sub-directories
    def _populate_from_directory(
        self, directory: PurePath, par: Object | None
    ) -> Tuple[Module, list[PurePath]]:
        drc = dir_children(directory)
        if drc.init is None:
            raise InitPyNotFound(
                "__init__.py not found in {}".format(directory))

        # Find main module of this directory
        main_mod = mod_from_file(drc.init)
        main_mod.parent = par
        self._populate_from_object(main_mod)

        # Then do the direct sub-modules
        for file in drc.files:
            mod = mod_from_file(file)
            mod.parent = main_mod
            main_mod.append_child(mod.name, mod)
            self._populate_from_object(mod)

        return (main_mod, drc.dirs)

    def _populate_from_object(self, ob: Object) -> None:
        pos = position_from_source_span(ob.source_span)
        self.db[pos] = ob
        for child in ob.children.values():
            self._populate_from_object(child)


class IncrementalProject:
    """
    Unlike Project which builds information from a given project root,
    IncrementalProject builds it in an online fashion. IncrementalProject
    accepts a Python file and its full package name. Then it creates the module
    for that file and inserts it into its database, patching parent and child pointers.
    """

    db: ObjectDb
    kw_fns: ObjectDb
    mod_db: dict[str, Module]

    def __init__(self) -> None:
        self.db = ObjectDb()
        self.kw_fns = ObjectDb()
        self.mod_db = {}

    def add_file(self, path: str, fullname: str) -> None:
        name_parts = fullname.split('.')
        par_mod: Module | NoneType = None
        mod_name = name_parts[-1]
        if len(name_parts) > 1:
            par_name = '.'.join(name_parts[:-1])
            if par_name in self.mod_db:
                par_mod = self.mod_db[par_name]

        mod = mod_from_file(path, mod_name)
        mod.parent = par_mod
        if par_mod:
            par_mod.children[mod.name] = mod

        self.mod_db[fullname] = mod
        new_obs = self._populate_from_object(mod)
        self._find_kw_fns(new_obs)

    def _populate_from_object(self, ob: Object) -> list[Tuple[Position, Object]]:
        pos = position_from_source_span(ob.source_span)
        self.db[pos] = ob
        obs = [(pos, ob)]
        for child in ob.children.values():
            new_obs = self._populate_from_object(child)
            obs.extend(new_obs)
        return obs

    def _find_kw_fns(self, obs: list[Tuple[Position, Object]]) -> None:
        for pos, ob in obs:
            if isinstance(ob, Function) and ob.has_kwargs_dict():
                self.kw_fns[pos] = ob
