def boxed(s: str, lpad: int = 2, rpad: int = 2) -> str:
    tot_len = len(s) + lpad + rpad
    out = '┌' + '─' * tot_len + '┐' + '\n'
    out += '│' + ' ' * lpad + s + ' ' * rpad + '│' + '\n'
    out += '└' + '─' * tot_len + '┘'
    return out


def tabled(words: list[str], tot_width: int = 80, spacing: int = 1) -> str:
    widths = _optimal_widths(words, tot_width, spacing)
    out = ''
    if widths is None:
        for word in words:
            out += word + '\n'
    else:
        for i, word in enumerate(words):
            col_idx = i % len(widths)
            if i > 0 and col_idx == 0:
                out += '\n'
            if col_idx == 0:
                out += ' ' * spacing
            out += _right_pad(word, widths[col_idx]) + ' ' * spacing
        out += '\n'
    return out


def horizontal_line(length: int) -> str:
    return '─' * length


def _right_pad(word: str, width: int) -> str:
    assert len(word) <= width
    pad_len = width - len(word)
    return word + ' ' * pad_len


def _optimal_widths(words: list[str], tot_width: int, spacing: int) -> list[int] | None:
    max_len = max(map(len, words))
    min_len = min(map(len, words))
    if max_len + 2 * spacing > tot_width:
        return None
    max_cols = min((tot_width - spacing) // (min_len + spacing), len(words))
    for i in range(max_cols, 0, -1):
        widths = _widths_for_col_cnt(words, tot_width, spacing, i)
        if widths is not None:
            return widths


def _widths_for_col_cnt(words: list[str], tot_width: int, spacing: int, col_cnt: int) -> list[int] | None:
    assert col_cnt > 0
    widths = [0] * col_cnt
    for i in range(len(words)):
        col_idx = i % col_cnt
        curr_size = len(words[i])
        widths[col_idx] = max(widths[col_idx], curr_size)
    tot_req_width = sum(widths) + (col_cnt + 1) * spacing
    return widths if tot_req_width <= tot_width else None
