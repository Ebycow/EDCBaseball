import sys
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Optional


class EdcbClient:
    def __init__(self, base_url: str, timeout: int = 15):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _fetch_xml(self, path: str, params: Optional[dict] = None) -> ET.Element:
        url = self.base_url + path
        if params:
            url += '?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        err = root.find('err')
        if err is not None:
            raise RuntimeError(f"EDCB Error: {err.text}")
        return root

    def get_events_for_service(self, onid: int, tsid: int, sid: int) -> list[dict]:
        root = self._fetch_xml('/api/EnumEventInfo', {
            'id': f'{onid}-{tsid}-{sid}',
            'basic': 0,
        })
        events = []
        for e in root.findall('.//eventinfo'):
            ev = self._parse_event(e)
            if ev is not None:
                events.append(ev)
        return events

    def _parse_event(self, e: ET.Element) -> Optional[dict]:
        title = e.findtext('event_name') or e.findtext('title') or ''
        start_date = e.findtext('startDate', '')
        start_time = e.findtext('startTime', '')
        if not start_date or not start_time:
            return None
        try:
            starttime = datetime.strptime(f'{start_date} {start_time}', '%Y/%m/%d %H:%M:%S')
        except ValueError:
            return None

        genres = []
        for ci in e.findall('contentInfo'):
            try:
                genres.append((int(ci.findtext('nibble1', '0')), int(ci.findtext('nibble2', '0'))))
            except ValueError:
                pass

        return {
            'onid': int(e.findtext('ONID', '0') or 0),
            'tsid': int(e.findtext('TSID', '0') or 0),
            'sid': int(e.findtext('SID', '0') or 0),
            'eid': int(e.findtext('eventID', '0') or 0),
            'title': title,
            'service': e.findtext('service_name', ''),
            'starttime': starttime,
            'duration_sec': int(e.findtext('duration', '0') or 0),
            'genres': genres,
            'text': e.findtext('event_text', ''),
        }
