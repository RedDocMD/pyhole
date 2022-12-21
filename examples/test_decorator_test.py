from pyhole import test_case, exec_cases, add_project, get_kwd_db
from pyhole.db import KeywordDb
from pyhole.project import Project
from pathlib import Path
import logging
import requests


@test_case
def test_get():
    requests.get("https://httpbin.org/get")


@test_case
def test_post():
    requests.post("https://httpbin.org/post", data={'key': 'value'})


@test_case
def test_session():
    sess = requests.Session()
    sess.headers.update({'x-test': 'true'})
    sess.get("https://httpbin.org/get")
    sess.post("https://httpbin.org/post")
    sess.patch("https://httpbin.org/patch")
    sess.delete("https://httpbin.org/delete")
    sess.put("https://httpbin.org/put")


@test_case
def test_json():
    resp = requests.get("https://httpbin.org/json")
    resp.json()


def grid_print(words):
    width = 20
    per_row = 5
    print('    ', end='')
    for i, word in enumerate(words):
        if i > 0 and i % per_row == 0:
            print()
            print('    ', end='')
        pad_len = width - len(word)
        pad = ' ' * pad_len
        print('{}{}'.format(word, pad), end='')
    print()


def print_fancy(kdb: KeywordDb) -> None:
    print('┌' + '─' * 19 + '┐')
    print('│ POSSIBLE KEYWORDS │')
    print('└' + '─' * 19 + '┘')
    for fn, kwds in kdb.items():
        print(f'  {fn}')
        fn_len = len('function') + 3 + len(str(fn.full_path())) + len(fn._format_args())
        print(' ' + '─' * (fn_len + 2))
        grid_print(kwds)
        print()


def print_simple(kdb: KeywordDb) -> None:
    for k, v in kdb.items():
        print(k, ":", v)


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s: %(message)s',
                        level=logging.WARNING)
    cwd = Path.cwd()
    # Run from project root
    root = cwd / ".venv" / "lib" / "python3.10" / "site-packages" / "requests"

    project = Project(root)
    # for fn in project.kw_fns.values():
    #     print(fn)
    add_project(project)
    exec_cases()
    kwd_db = get_kwd_db()
    # print_simple(kwd_db)
    for fn in project.kw_fns.values():
        if fn not in kwd_db.items():
            print(fn)
