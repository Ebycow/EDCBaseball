import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baseball import _merge_event_relays, _select_ttrec_targets


def _event(channel_name: str, starttime: datetime, duration_sec: int = 3600) -> dict:
    return {
        'title': '大谷出場予定　ＭＬＢ２０２６「マーリンズ」対「ドジャース」[二]',
        'channel_name': channel_name,
        'starttime': starttime,
        'duration_sec': duration_sec,
        'is_live': True,
        'is_mlb': True,
        'is_nhk': True,
        'onid': 4,
        'tsid': 16625,
        'sid': 101 if channel_name == 'NHK BS' else 102,
        'eid': hash((channel_name, starttime)) & 0xFFFFFFFF,
    }


class EventRelayTests(unittest.TestCase):
    def test_merge_event_relays_when_nhk_returns_to_original_channel(self):
        events = [
            _event('NHK BS', datetime(2026, 4, 29, 11, 0), 3300),
            _event('NHK BS 2', datetime(2026, 4, 29, 11, 55), 1800),
            _event('NHK BS', datetime(2026, 4, 29, 12, 25), 1800),
        ]

        merged = _merge_event_relays(events)

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]['channel_name'], 'NHK BS -> NHK BS 2 -> NHK BS')
        self.assertTrue(merged[0]['is_event_relay'])

    def test_select_ttrec_targets_skips_returned_nhk_relay_segment(self):
        events = [
            _event('NHK BS', datetime(2026, 4, 29, 11, 0), 3300),
            _event('NHK BS 2', datetime(2026, 4, 29, 11, 55), 1800),
            _event('NHK BS', datetime(2026, 4, 29, 12, 25), 1800),
        ]

        targets, skipped = _select_ttrec_targets(events)

        self.assertEqual(len(targets), 1)
        self.assertEqual(len(skipped), 2)
        self.assertEqual(targets[0]['channel_name'], 'NHK BS -> NHK BS 2 -> NHK BS')


if __name__ == '__main__':
    unittest.main()
