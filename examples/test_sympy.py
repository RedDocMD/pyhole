from pyhole import test_case, exec_cases, add_project, get_kwd_db
from pyhole.project import Project
from pathlib import Path
import logging


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "sympy"

    project = Project(root)
    print(len(project.db), "objects")
    print(len(project.kw_fns), "keyword functions")
    # for fn in project.kw_fns.values():
    #     print(fn)
    add_project(project)
    exec_cases()
    kwd_db = get_kwd_db()
    print("DB:", kwd_db)
