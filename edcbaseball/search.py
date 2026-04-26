import sys
from datetime import datetime, timedelta
from typing import Optional

from .client import EdcbClient
from .channels import BASEBALL_CHANNELS
from .teams import NPB_TEAMS, MLB_KEYWORDS

# 野球ジャンルだが試合中継ではない番組タイトルパターン
_EXCLUDE_TITLE_PATTERNS = [
    "プロ野球ニュース",
    "ファーム",
    "MLBイッキ見",
    "練習"
]


def _is_excluded(title: str) -> bool:
    return any(pat in title for pat in _EXCLUDE_TITLE_PATTERNS)


def _is_baseball_genre(genres: list) -> bool:
    # Check only the PRIMARY (first) genre entry.
    # Sports channels like GAORA add a secondary (1,1) tag to non-baseball shows
    # (golf, fishing) hosted by ex-players; secondary tags must be ignored.
    if not genres:
        return False
    n1, n2 = genres[0]
    return n1 == 1 and n2 == 1


def _is_live(title: str, channel: dict = None) -> bool:
    if '[生]' in title:
        return True
    # NHK BS MLB game broadcasts are live but don't use [生].
    # Identified by "「チーム名」対「チーム名」" pattern in MLB title.
    if channel and channel.get('nhk') and _is_mlb(title) and '対「' in title:
        return True
    return False


def _is_mlb(title: str) -> bool:
    return any(kw in title for kw in MLB_KEYWORDS)


def _match_mlb_source(channel: dict, mlb_source: str) -> bool:
    if mlb_source == 'all':
        return True
    if mlb_source == 'nhk':
        return bool(channel.get('nhk'))
    if mlb_source == 'jsports':
        return channel.get('name', '').startswith('J SPORTS')
    return True


def _find_npb_team(title: str) -> Optional[str]:
    for team in NPB_TEAMS:
        if any(kw in title for kw in team['keywords']):
            return team['short']
    return None


def _resolve_team_keywords(team_query: str) -> list[str]:
    """Return the keyword list for a team query (short name, full name, or keyword)."""
    q = team_query.strip()
    for team in NPB_TEAMS:
        if q in [team['name'], team['short']] or q in team['keywords']:
            return team['keywords']
    # Fallback: treat the raw query as a keyword
    return [q]


def search_baseball(
    base_url: str,
    team: Optional[str] = None,
    mlb_only: bool = False,
    mlb_source: str = 'all',
    npb_only: bool = False,
    days: int = 7,
    live_only: bool = False,
    verbose: bool = False,
) -> list[dict]:
    client = EdcbClient(base_url)
    now = datetime.now()
    cutoff = now + timedelta(days=days)

    team_keywords = _resolve_team_keywords(team) if team else None

    results = []

    for ch in BASEBALL_CHANNELS:
        try:
            events = client.get_events_for_service(ch['onid'], ch['tsid'], ch['sid'])
        except Exception as exc:
            if verbose:
                print(f"[skip] {ch['name']}: {exc}", file=sys.stderr)
            continue

        for ev in events:
            end_time = ev['starttime'] + timedelta(seconds=ev['duration_sec'])
            if end_time <= now or ev['starttime'] > cutoff:
                continue

            title = ev['title']

            # Genre-based filter (primary genre only)
            if not _is_baseball_genre(ev['genres']):
                continue

            if _is_excluded(title):
                continue

            # NHK BS uses event relay: the 1-minute "stub" events that trigger
            # sub-channel handoff are not the main recording target; skip them.
            if ch.get('nhk') and ev['duration_sec'] < 300:
                continue

            if live_only and not _is_live(title, ch):
                continue

            # --team と --mlb は OR 条件: どちらかにマッチすればよい
            if mlb_only and team_keywords:
                if not (_is_mlb(title) or any(kw in title for kw in team_keywords)):
                    continue
            elif mlb_only:
                if not _is_mlb(title):
                    continue
            elif team_keywords:
                if not any(kw in title for kw in team_keywords):
                    continue

            # --npb は AND 条件: MLB を除外する
            if npb_only and _is_mlb(title):
                continue

            if _is_mlb(title) and not _match_mlb_source(ch, mlb_source):
                continue

            results.append({
                **ev,
                'channel_name': ch['name'],
                'is_nhk': bool(ch.get('nhk')),
                'is_live': _is_live(title, ch),
                'is_mlb': _is_mlb(title),
                'npb_team': _find_npb_team(title),
            })

    results.sort(key=lambda x: x['starttime'])
    return results
