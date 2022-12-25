def boxed(s: str, lpad: int = 2, rpad: int = 2) -> str:
    tot_len = len(s) + lpad + rpad
    out = '┌' + '─' * tot_len + '┐' + '\n'
    out += '│' + ' ' * lpad + s + ' ' * rpad + '│' + '\n'
    out += '└' + '─' * tot_len + '┘'
    return out

