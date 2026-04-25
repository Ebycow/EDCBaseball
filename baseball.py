#!/usr/bin/env python3
"""
EDCBaseball - EDCBから野球中継の放送を検索するツール

使用例:
  python baseball.py                     # 全球団 + MLB を7日分表示
  python baseball.py --team 阪神         # 阪神戦のみ
  python baseball.py --mlb               # MLBのみ
  python baseball.py --npb               # NPB（国内プロ野球）のみ
  python baseball.py --live              # 生放送のみ
  python baseball.py --mlb --live        # MLB生放送のみ
  python baseball.py --npb --live        # NPB生放送のみ
  python baseball.py --days 14           # 2週間分
  python baseball.py --url http://...    # EDCBサーバーURL指定
"""

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from edcbaseball.search import search_baseball
from edcbaseball.chart import render_chart
from edcbaseball.teams import NPB_TEAMS

# Default EDCB server URL. Override in config.local.py (gitignored) or use --url.
DEFAULT_EDCB_URL = "http://localhost:5510"
try:
    from config_local import EDCB_URL as DEFAULT_EDCB_URL  # type: ignore
except ImportError:
    pass

_WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]
_RELAY_GAP = timedelta(minutes=5)


def _fmt_duration(seconds: int) -> str:
    h, m = divmod(seconds, 3600)
    m = m // 60
    return f"{h}時間{m:02d}分" if h > 0 else f"{m}分"


def _fmt_event(ev: dict) -> str:
    dt: datetime = ev['starttime']
    wd = _WEEKDAY_JA[dt.weekday()]
    date_str = dt.strftime(f'%m/%d({wd})')
    time_str = dt.strftime('%H:%M')
    duration = _fmt_duration(ev['duration_sec'])
    live_mark = '[生]' if ev['is_live'] else '[録]'
    league = '[MLB]' if ev['is_mlb'] else '[NPB]'
    relay_note = 'イベントリレー, ' if ev.get('is_event_relay') else ''
    return f"  {date_str} {time_str} {live_mark}{league} [{ev['channel_name']}] {ev['title']} ({relay_note}{duration})"


def _can_merge_event_relay(prev: dict, cur: dict) -> bool:
    if not (prev.get('is_nhk') and cur.get('is_nhk')):
        return False
    if not (prev['is_live'] and cur['is_live']):
        return False
    if prev['title'] != cur['title']:
        return False
    if prev['is_mlb'] != cur['is_mlb']:
        return False
    if prev['channel_name'] == cur['channel_name']:
        return False

    prev_end = prev['starttime'] + timedelta(seconds=prev['duration_sec'])
    gap = cur['starttime'] - prev_end
    return timedelta(0) <= gap <= _RELAY_GAP


def _find_relay_merge_target(merged: list[dict], cur: dict) -> Optional[dict]:
    for prev in reversed(merged):
        prev_end = prev['starttime'] + timedelta(seconds=prev['duration_sec'])
        if cur['starttime'] - prev_end > _RELAY_GAP:
            break
        if _can_merge_event_relay(prev, cur):
            return prev
    return None


def _merge_event_relays(events: list[dict]) -> list[dict]:
    if not events:
        return []

    merged: list[dict] = []
    for ev in sorted(events, key=lambda x: x['starttime']):
        cur = dict(ev)
        cur.setdefault('relay_channels', [cur['channel_name']])

        prev = _find_relay_merge_target(merged, cur)
        if prev is not None:
            relay_channels = list(prev.get('relay_channels', [prev['channel_name']]))
            if cur['channel_name'] not in relay_channels:
                relay_channels.append(cur['channel_name'])

            merged_end = max(
                prev['starttime'] + timedelta(seconds=prev['duration_sec']),
                cur['starttime'] + timedelta(seconds=cur['duration_sec']),
            )
            prev['duration_sec'] = int((merged_end - prev['starttime']).total_seconds())
            prev['relay_channels'] = relay_channels
            prev['channel_name'] = ' -> '.join(relay_channels)
            prev['is_event_relay'] = True
            continue

        merged.append(cur)

    return merged


def _print_team_list():
    print("NPBチーム一覧:")
    for t in NPB_TEAMS:
        kw_str = ", ".join(t['keywords'])
        print(f"  {t['short']:8s}  ({kw_str})")
    print("\nMLBは --mlb フラグ、または --team ドジャース などチーム名で絞り込めます")


def main():
    parser = argparse.ArgumentParser(
        description='EDCBから野球中継の放送スケジュールを検索します',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--url', default=DEFAULT_EDCB_URL,
                        help=f'EDCBサーバーURL (デフォルト: {DEFAULT_EDCB_URL})')
    parser.add_argument('--team', '-t', metavar='TEAM',
                        help='球団名でフィルタ (例: 阪神, 巨人, ドジャース)')
    parser.add_argument('--mlb', action='store_true',
                        help='MLBのみ表示')
    parser.add_argument('--npb', action='store_true',
                        help='NPB（国内プロ野球）のみ表示')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='何日先まで検索 (デフォルト: 7)')
    parser.add_argument('--live', '-l', action='store_true',
                        help='生放送のみ表示')
    parser.add_argument('--chart', '-c', action='store_true',
                        help='時系列チャート（タイムライン）で表示')
    parser.add_argument('--teams', action='store_true',
                        help='NPBチーム一覧を表示して終了')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='チャンネル取得エラーなどの詳細を表示')
    args = parser.parse_args()

    if args.teams:
        _print_team_list()
        return

    print(f"EDCBサーバー : {args.url}")
    print(f"検索期間     : 今から {args.days} 日間")
    filters = []
    if args.team and args.mlb:
        filters.append(f"球団={args.team} OR MLB")
    elif args.team:
        filters.append(f"球団={args.team}")
    elif args.mlb:
        filters.append("MLBのみ")
    if args.npb:
        filters.append("NPBのみ")
    if args.live:
        filters.append("生放送のみ")
    if filters:
        print(f"フィルタ     : {', '.join(filters)}")
    print()

    try:
        events = search_baseball(
            base_url=args.url,
            team=args.team,
            mlb_only=args.mlb,
            npb_only=args.npb,
            days=args.days,
            live_only=args.live,
            verbose=args.verbose,
        )
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        sys.exit(1)

    if not events:
        print("該当する番組が見つかりませんでした。")
        return

    if args.chart:
        render_chart(events)
        return

    events = _merge_event_relays(events)

    # Group by date
    by_date: dict[str, list] = defaultdict(list)
    for ev in events:
        dt: datetime = ev['starttime']
        wd = _WEEKDAY_JA[dt.weekday()]
        key = dt.strftime(f'%Y/%m/%d ({wd})')
        by_date[key].append(ev)

    total = 0
    for date_key in sorted(by_date.keys()):
        print(f"── {date_key} " + "─" * 35)
        for ev in sorted(by_date[date_key], key=lambda x: x['starttime']):
            print(_fmt_event(ev))
            total += 1
        print()

    print(f"合計 {total} 件")


if __name__ == '__main__':
    main()
