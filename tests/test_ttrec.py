import unittest
from datetime import datetime

from edcbaseball.ttrec import TTRecClient


def _event() -> dict:
    return {
        'onid': 6,
        'tsid': 24608,
        'sid': 296,
        'eid': 26341,
        'starttime': datetime(2026, 5, 10, 13, 25),
        'duration_sec': 18300,
    }


def _reserve() -> dict:
    return {
        'networkId': 6,
        'transportStreamId': 24608,
        'serviceId': 296,
        'eventId': 26341,
        'startTime': '2026-05-10T13:25:00',
        'duration': 18300,
    }


class FakeTTRecClient(TTRecClient):
    def __init__(self, responses: list, verify_attempts: int = 1):
        super().__init__('http://example.invalid', verify_attempts=verify_attempts, verify_interval=0)
        self.responses = list(responses)

    def _request(self, method: str, path: str, payload=None):
        if not self.responses:
            raise AssertionError(f'unexpected request: {method} {path}')
        return self.responses.pop(0)


class TTRecClientTests(unittest.TestCase):
    def test_reserve_default_requires_reserve_list_confirmation(self):
        client = FakeTTRecClient([
            {'success': True, 'note': 'accepted'},
            [],
        ])

        with self.assertRaisesRegex(RuntimeError, '予約一覧に反映されませんでした'):
            client.reserve_default(_event())

    def test_reserve_default_accepts_confirmed_reserve(self):
        client = FakeTTRecClient([
            {'success': True},
            [_reserve()],
        ])

        self.assertEqual(client.reserve_default(_event()), {'success': True})

    def test_reserve_default_retries_confirmation(self):
        client = FakeTTRecClient([
            {'success': True},
            [],
            [_reserve()],
        ], verify_attempts=2)

        self.assertEqual(client.reserve_default(_event()), {'success': True})

    def test_reserve_default_rejects_explicit_failure_response(self):
        client = FakeTTRecClient([
            {'success': False, 'message': 'failed'},
        ])

        with self.assertRaisesRegex(RuntimeError, 'failed'):
            client.reserve_default(_event())


if __name__ == '__main__':
    unittest.main()
