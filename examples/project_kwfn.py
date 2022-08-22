from pyhole.project import Project
from pathlib import Path

if __name__ == "__main__":
    cwd = Path.cwd()
    # Run from project root
    root = cwd / "requests" / "requests"
    project = Project(root)
    for pos, ob in project.kw_fns.items():
        print("{} => {}".format(ob, pos))
