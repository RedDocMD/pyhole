from importlib import abc, machinery
from typing import Optional, Sequence, Union, Any
import types
import sys
import logging as lg
import _frozen_importlib  # type: ignore[import]
import _frozen_importlib_external  # type: ignore[import]
from .project import IncrementalProject


class PyholeMetaPathFinder(abc.MetaPathFinder):
    """
    Custom meta path finder to add explore a project.
    Heavily inspired by https://github.com/google/atheris/blob/master/src/import_hook.py
    """
    project: IncrementalProject

    def __init__(self, project: IncrementalProject) -> None:
        super().__init__()
        self.project = project

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[Union[bytes, str]]],
        target: Optional[types.ModuleType] = None
    ) -> Optional[machinery.ModuleSpec]:
        """
        Currently, this doesn't actually "find" a spec.
        Rather, it just bootstraps onto another loader to add
        stuff into the project.
        """
        package_name = fullname.split(".")[0]

        if package_name == "pyhole":
            return None

        found_pyhole = False
        for meta in sys.meta_path:
            if not found_pyhole:
                if meta is self:
                    found_pyhole = True
                continue

            if not hasattr(meta, 'find_spec'):
                continue

            spec = meta.find_spec(fullname, path, target)
            if spec is None or spec.loader is None:
                continue

            if hasattr(spec.loader, 'path'):
                lg.debug("Importing path: %s (%s)", spec.loader.path, fullname)
                self.project.add_file(spec.loader.path, fullname)
            else:
                lg.warn('Loader returned for %s has no path', fullname)

            if isinstance(spec.loader, _frozen_importlib_external.SourceFileLoader):
                spec.loader = PyholeSourceFileLoader(
                    spec.loader.name, spec.loader.path)
                return spec

            return None


class PyholeSourceFileLoader(_frozen_importlib_external.SourceFileLoader):
    def __init__(self, name: str, path: str) -> None:
        super().__init__(name, path)

    def exec_module(self, module):
        lg.debug("Source file loader loading: %s", self.path)
        super().exec_module(module)

    def get_code(self, fullname):
        lg.debug("Getting code for %s", self.path)
        code = super().get_code(fullname)
        lg.debug(code)
        lg.debug(dir(code))
        lg.debug(code.co_names)
        return code


class HookManager:
    project: IncrementalProject

    def __init__(self, project: IncrementalProject) -> None:
        self.project = project

    def __enter__(self) -> "HookManager":
        i = 0
        while i < len(sys.meta_path):
            if isinstance(sys.meta_path[i], PyholeMetaPathFinder):
                return self
            i += 1

        i = 0
        while i < len(sys.meta_path) and sys.meta_path[i] in [
            _frozen_importlib.BuiltinImporter, _frozen_importlib.FrozenImporter
        ]:
            i += 1

        sys.meta_path.insert(i, PyholeMetaPathFinder(self.project))

        return self

    def __exit__(self, *args: Any) -> None:
        i = 0
        while i < len(sys.meta_path):
            if isinstance(sys.meta_path[i], PyholeMetaPathFinder):
                sys.meta_path.pop(i)
            else:
                i += 1


def populate_db(project: IncrementalProject):
    return HookManager(project)
