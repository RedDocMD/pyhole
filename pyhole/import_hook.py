from importlib import abc, machinery
from typing import Optional, Sequence, Union, Any
import types
import sys
import logging as lg
import _frozen_importlib  # type: ignore[import]
import _frozen_importlib_external  # type: ignore[import]


class PyholeMetaPathFinder(abc.MetaPathFinder):
    """
    Custom meta path finder to add explore a project.
    Heavily inspired by https://github.com/google/atheris/blob/master/src/import_hook.py
    """

    def __init__(self) -> None:
        super().__init__()

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
                lg.debug("Importing path: %s", spec.loader.path)
            else:
                lg.debug('Loader returned for %s has no path', fullname)

            return None


class HookManager:
    def __init__(self) -> None:
        pass

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

        sys.meta_path.insert(i, PyholeMetaPathFinder())

        return self

    def __exit__(self, *args: Any) -> None:
        i = 0
        while i < len(sys.meta_path):
            if isinstance(sys.meta_path[i], PyholeMetaPathFinder):
                sys.meta_path.pop(i)
            else:
                i += 1


def populate_db():
    return HookManager()
