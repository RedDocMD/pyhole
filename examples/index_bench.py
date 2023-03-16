from pyhole.project import Project
from pathlib import Path
import time


def bench_project(path):
    start = time.time()
    project = Project(path)
    end = time.time()
    print(end - start, "s")
    return project


def project_stats(proj):
    ob_cnt = len(proj.db)
    kw_cnt = len(proj.kw_fns)
    print("Object cnt", ob_cnt, "Keyword fn cnt", kw_cnt)


cwd = Path.cwd()
root = cwd.parent / "parse-py" / "projects"
paths = [
    "/home/dknite/work/stuff/scikit-learn-main/sklearn",
    "/home/dknite/work/stuff/pygments-master/pygments",
    "/home/dknite/work/stuff/numpy-main/numpy",
    root / "requests" / "requests",
    root / "pandas" / "pandas",
    root / "sympy" / "sympy",
    # cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "sympy",
]

for path in paths:
    print(path)
    project = bench_project(path)
    project_stats(project)
