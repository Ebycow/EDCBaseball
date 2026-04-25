#!/usr/bin/env python3
"""
EDCBaseball - EDCBから野球中継の放送を検索するツール

使用例:
  python baseball.py                     # 全球団 + MLB を7日分表示
  python baseball.py --team 阪神         # 阪神戦のみ
  python baseball.py --mlb               # MLBのみ
  python baseball.py --mlb --mlb-source nhk      # MLBのうちNHKのみ
  python baseball.py --mlb --mlb-source jsports  # MLBのうちJ SPORTSのみ
  python baseball.py --live --team 中日 --mlb --ttrec   # 検索結果をTTRecに予約
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
from edcbaseball.ttrec import TTRecClient, find_duplicate_reserves

# Default EDCB server URL. Override in config.local.py (gitignored) or use --url.
DEFAULT_EDCB_URL = "http://localhost:5510"
DEFAULT_TTREC_URL = "http://192.168.222.110:40152"
try:
    from config_local import EDCB_URL as DEFAULT_EDCB_URL  # type: ignore
except ImportError:
    pass
try:
    from config_local import TTREC_URL as DEFAULT_TTREC_URL  # type: ignore
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


def _is_same_relay_program(prev: dict, cur: dict) -> bool:
    if not (prev.get('is_nhk') and cur.get('is_nhk')):
        return False
    if not (prev['is_live'] and cur['is_live']):
        return False
    if prev['title'] != cur['title']:
        return False
    if prev['is_mlb'] != cur['is_mlb']:
        return False
    return True


def _can_follow_event_relay(prev: dict, cur: dict) -> bool:
    if not _is_same_relay_program(prev, cur):
        return False
    prev_end = prev['starttime'] + timedelta(seconds=prev['duration_sec'])
    gap = cur['starttime'] - prev_end
    if not (timedelta(0) <= gap <= _RELAY_GAP):
        return False

    prev_last_channel = prev.get('relay_last_channel', prev['channel_name'])
    return prev_last_channel != cur['channel_name'] or prev.get('is_event_relay', False)


def _find_relay_merge_target(merged: list[dict], cur: dict) -> Optional[dict]:
    for prev in reversed(merged):
        prev_end = prev['starttime'] + timedelta(seconds=prev['duration_sec'])
        if cur['starttime'] - prev_end > _RELAY_GAP:
            break
        if _can_follow_event_relay(prev, cur):
            return prev
    return None


def _extend_relay_chain(prev: dict, cur: dict) -> None:
    relay_channels = list(prev.get('relay_channels', [prev['channel_name']]))
    if not relay_channels or relay_channels[-1] != cur['channel_name']:
        relay_channels.append(cur['channel_name'])

    merged_end = max(
        prev['starttime'] + timedelta(seconds=prev['duration_sec']),
        cur['starttime'] + timedelta(seconds=cur['duration_sec']),
    )
    prev['duration_sec'] = int((merged_end - prev['starttime']).total_seconds())
    prev['relay_channels'] = relay_channels
    prev['relay_last_channel'] = cur['channel_name']
    prev['channel_name'] = ' -> '.join(relay_channels)
    prev['is_event_relay'] = True


def _merge_event_relays(events: list[dict]) -> list[dict]:
    if not events:
        return []

    merged: list[dict] = []
    for ev in sorted(events, key=lambda x: x['starttime']):
        cur = dict(ev)
        cur.setdefault('relay_channels', [cur['channel_name']])
        cur.setdefault('relay_last_channel', cur['channel_name'])

        prev = _find_relay_merge_target(merged, cur)
        if prev is not None:
            _extend_relay_chain(prev, cur)
            continue

        merged.append(cur)

    return merged


def _select_ttrec_targets(events: list[dict]) -> tuple[list[dict], list[dict]]:
    if not events:
        return [], []

    targets: list[dict] = []
    skipped_relays: list[dict] = []

    for ev in sorted(events, key=lambda x: x['starttime']):
        prev = _find_relay_merge_target(targets, ev)
        if prev is not None:
            _extend_relay_chain(prev, ev)
            skipped_relays.append(ev)
            continue
        target = dict(ev)
        target.setdefault('relay_channels', [target['channel_name']])
        target.setdefault('relay_last_channel', target['channel_name'])
        targets.append(target)

    return targets, skipped_relays


def _print_team_list():
    print("NPBチーム一覧:")
    for t in NPB_TEAMS:
        kw_str = ", ".join(t['keywords'])
        print(f"  {t['short']:8s}  ({kw_str})")
    print("\nMLBは --mlb フラグ、または --team ドジャース などチーム名で絞り込めます")


def _reserve_with_ttrec(events: list[dict], ttrec_url: str) -> None:
    reserve_targets, skipped_relays = _select_ttrec_targets(events)
    client = TTRecClient(ttrec_url)
    reserves = client.get_reserves()
    pending, duplicates = find_duplicate_reserves(reserve_targets, reserves)

    print(f"TTRec        : {ttrec_url}")
    if skipped_relays:
        print(f"追従省略     : {len(skipped_relays)} 件")
    print(f"重複予約     : {len(duplicates)} 件")
    print(f"新規予約候補 : {len(pending)} 件")

    for event in skipped_relays:
        print(f"  [追従] [{event['channel_name']}] {event['title']}")

    for event, reserve in duplicates:
        print(f"  [重複] [{event['channel_name']}] {event['title']} ({reserve.get('startTime', '-')})")

    if not pending:
        print("TTRec予約     : 新規追加はありませんでした")
        return

    success = 0
    for event in pending:
        client.reserve_default(event)
        print(f"  [予約] [{event['channel_name']}] {event['title']}")
        success += 1

    print(f"TTRec予約     : {success} 件追加しました")


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
    parser.add_argument('--mlb-source', choices=['all', 'nhk', 'jsports'], default='all',
                        help='MLBの放送元を選択 (all, nhk, jsports)')
    parser.add_argument('--npb', action='store_true',
                        help='NPB（国内プロ野球）のみ表示')
    parser.add_argument('--days', '-d', type=int, default=7,
                        help='何日先まで検索 (デフォルト: 7)')
    parser.add_argument('--live', '-l', action='store_true',
                        help='生放送のみ表示')
    parser.add_argument('--chart', '-c', action='store_true',
                        help='時系列チャート（タイムライン）で表示')
    parser.add_argument('--ttrec', action='store_true',
                        help='検索結果をTTRecに予約追加（重複チェックあり）')
    parser.add_argument('--ttrec-url', default=DEFAULT_TTREC_URL,
                        help=f'TTRec HTTP API URL (デフォルト: {DEFAULT_TTREC_URL})')
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
    if args.mlb and args.mlb_source != 'all':
        source_labels = {
            'nhk': 'MLBソース=NHK',
            'jsports': 'MLBソース=J SPORTS',
        }
        filters.append(source_labels[args.mlb_source])
    if args.npb:
        filters.append("NPBのみ")
    if args.live:
        filters.append("生放送のみ")
    if args.ttrec:
        filters.append("TTRec予約")
    if filters:
        print(f"フィルタ     : {', '.join(filters)}")
    print()

    try:
        events = search_baseball(
            base_url=args.url,
            team=args.team,
            mlb_only=args.mlb,
            mlb_source=args.mlb_source,
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

    raw_events = list(events)

    if args.chart:
        render_chart(events)
        return

    if args.ttrec:
        try:
            _reserve_with_ttrec(raw_events, args.ttrec_url)
            print()
        except Exception as exc:
            print(f"TTRec予約エラー: {exc}", file=sys.stderr)
            sys.exit(1)

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
