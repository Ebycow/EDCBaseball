"""ASCII timeline (chart) renderer for baseball schedules."""

import os
import re
import unicodedata
from datetime import timedelta
from collections import defaultdict
from typing import Optional

from .channels import BASEBALL_CHANNELS
from .teams import extract_matchup, MLB_KEYWORDS

_WEEKDAY = ["月", "火", "水", "木", "金", "土", "日"]
_CHANNEL_ORDER = {ch['name']: i for i, ch in enumerate(BASEBALL_CHANNELS)}

# Title abbreviation patterns applied in order
_TITLE_ABBREV = [
    (re.compile(r'\[[^\]]*\]'), ''),                      # [生][字][再] 等を除去
    (re.compile(r'プロ野球\d{4}\s*'), ''),                # "プロ野球2026 " を除去
    (re.compile(r'メジャーリーグ中継\d{4}\s*'), 'MLB '), # "メジャーリーグ中継2026 " → "MLB "
    (re.compile(r'ＤＲＡＭＡＴＩＣ\s*ＢＡＳＥＢＡＬＬ\s*\d{4}\s*'), ''),
    (re.compile(r'\(\d+/\d+\)$'), ''),                    # 末尾の (4/28) を除去
    (re.compile(r'^\s+|\s+$'), ''),                       # 前後の空白
]


def _abbrev(title: str) -> str:
    for pat, repl in _TITLE_ABBREV:
        title = pat.sub(repl, title)
    return title.strip()


def _dw(c: str) -> int:
    """Display width of a single character (1 or 2)."""
    return 2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1


def _str_dw(s: str) -> int:
    return sum(_dw(c) for c in s)


def _render_row(n_cols: int, events: list[dict]) -> str:
    """Build a display row of exactly n_cols terminal columns.

    Uses None as placeholder for the right half of a double-width character so
    that `_join()` always produces a string whose display width equals n_cols.
    """
    row: list = [' '] * n_cols

    def _fill(s: int, e: int, char: str) -> None:
        for k in range(s, min(e, n_cols)):
            row[k] = char

    def _overlay(start_col: int, end_col: int, text: str) -> None:
        pos = start_col
        for c in text:
            cw = _dw(c)
            if pos + cw > end_col:
                break
            row[pos] = c
            if cw == 2 and pos + 1 < n_cols:
                row[pos + 1] = None  # right-half placeholder
            pos += cw

    for ev in events:
        s, e = ev['_slot_start'], ev['_slot_end']
        blen = e - s
        if blen < 1:
            blen = 1
            e = s + 1

        fill = '█' if ev['is_live'] else '▒'
        _fill(s, e, fill)

        if blen >= 4:
            is_mlb = any(kw in ev['title'] for kw in MLB_KEYWORDS)
            label = ('' if is_mlb else extract_matchup(ev['title'])) or _abbrev(ev['title'])
            # Overlay label starting 1 col after block start, leaving 1 col at end
            _overlay(s + 1, e - 1, label)

    return ''.join(c for c in row if c is not None)


def render_chart(events: list[dict], term_width: Optional[int] = None) -> None:
    if not events:
        print("該当する番組が見つかりませんでした。")
        return

    if term_width is None:
        try:
            term_width = os.get_terminal_size().columns
        except OSError:
            term_width = 100

    # Group by date then channel
    by_date: dict = defaultdict(lambda: defaultdict(list))
    for ev in events:
        by_date[ev['starttime'].date()][ev['channel_name']].append(ev)

    for day in sorted(by_date.keys()):
        wd = _WEEKDAY[day.weekday()]
        ch_map = by_date[day]
        all_evs = [ev for evs in ch_map.values() for ev in evs]

        # Time window (rounded to hours)
        t_start = min(ev['starttime'] for ev in all_evs).replace(minute=0, second=0, microsecond=0)
        t_end_raw = max(ev['starttime'] + timedelta(seconds=ev['duration_sec']) for ev in all_evs)
        t_end = t_end_raw.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        total_min = int((t_end - t_start).total_seconds() / 60)

        # Channel name column width (display width)
        ch_col = max(_str_dw(ch) for ch in ch_map) + 1

        # Available columns for the timeline
        avail = term_width - ch_col - 1  # -1 for "│"
        if avail < 12:
            avail = 12

        # Pick min_per_char: smallest "nice" value where n_slots ≤ avail
        min_per_char = next(
            (n for n in [5, 10, 15, 20, 30, 60] if total_min / n <= avail),
            60
        )
        n_slots = total_min // min_per_char

        # Pre-compute slot positions for each event
        for ev in all_evs:
            s_min = (ev['starttime'] - t_start).total_seconds() / 60
            e_min = s_min + ev['duration_sec'] / 60
            ev['_slot_start'] = max(0, round(s_min / min_per_char))
            ev['_slot_end'] = min(n_slots, round(e_min / min_per_char))

        # ── Time axis ──────────────────────────────────────────
        time_row = [' '] * n_slots
        sep_row = ['─'] * n_slots
        for i in range(n_slots):
            t = t_start + timedelta(minutes=i * min_per_char)
            if t.minute == 0:
                sep_row[i] = '┬'
                label = f"{t.hour:02d}"
                for j, c in enumerate(label):
                    if i + j < n_slots:
                        time_row[i + j] = c

        pad = ' ' * ch_col
        print(f"\n{'━' * term_width}")
        print(f"  {day.strftime('%Y/%m/%d')} ({wd})  [1マス={min_per_char}分]")
        print()
        print(f"{pad}│{''.join(time_row)}")
        print(f"{pad}┼{''.join(sep_row)}")

        # ── Channel rows ───────────────────────────────────────
        sorted_chs = sorted(ch_map.keys(), key=lambda c: _CHANNEL_ORDER.get(c, 999))
        for ch in sorted_chs:
            dw = _str_dw(ch)
            label = ch + ' ' * (ch_col - dw)
            content = _render_row(n_slots, ch_map[ch])
            print(f"{label}│{content}")

        print()
