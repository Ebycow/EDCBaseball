import json
import urllib.error
import urllib.request
from typing import Optional


class TTRecClient:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(self, method: str, path: str, payload: Optional[dict] = None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read()
        except urllib.error.HTTPError as exc:
            body = exc.read()
            try:
                err = json.loads(body.decode('utf-8'))
            except Exception:
                err = {'error': body.decode('utf-8', errors='replace') or str(exc)}
            raise RuntimeError(err.get('error') or f'HTTP {exc.code}')
        except urllib.error.URLError as exc:
            raise RuntimeError(f'TTRec API に接続できません: {exc.reason}') from exc

        if not body:
            return None
        return json.loads(body.decode('utf-8'))

    def get_reserves(self) -> list[dict]:
        data = self._request('GET', '/api/ttrec/reserves')
        if isinstance(data, dict) and data.get('error'):
            raise RuntimeError(data['error'])
        return data or []

    def reserve_default(self, event: dict):
        payload = {
            'onid': event['onid'],
            'tsid': event['tsid'],
            'sid': event['sid'],
            'eid': event['eid'],
            'startTime': event['starttime'].strftime('%Y-%m-%dT%H:%M:%S'),
            'duration': event['duration_sec'],
        }
        return self._request('POST', '/api/ttrec/reserve/default', payload)


def _same_event(lhs: dict, rhs: dict) -> bool:
    return (
        lhs.get('onid') == rhs.get('networkId')
        and lhs.get('tsid') == rhs.get('transportStreamId')
        and lhs.get('sid') == rhs.get('serviceId')
        and lhs.get('eid') == rhs.get('eventId')
    )


def _same_timeslot(lhs: dict, rhs: dict) -> bool:
    start = lhs['starttime'].strftime('%Y-%m-%dT%H:%M:%S')
    return (
        rhs.get('networkId') == lhs.get('onid')
        and rhs.get('transportStreamId') == lhs.get('tsid')
        and rhs.get('serviceId') == lhs.get('sid')
        and rhs.get('startTime') == start
        and int(rhs.get('duration') or 0) == lhs.get('duration_sec')
    )


def find_duplicate_reserves(events: list[dict], reserves: list[dict]) -> tuple[list[dict], list[tuple[dict, dict]]]:
    new_events: list[dict] = []
    duplicates: list[tuple[dict, dict]] = []

    for event in events:
        match = next((reserve for reserve in reserves if _same_event(event, reserve)), None)
        if match is None:
            match = next((reserve for reserve in reserves if _same_timeslot(event, reserve)), None)
        if match is None:
            new_events.append(event)
        else:
            duplicates.append((event, match))

    return new_events, duplicates
