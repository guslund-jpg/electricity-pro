"""Keep existing export checkpoints usable without a running HA instance."""

from datetime import timedelta
import json

import pytest

from custom_components.electricity_pro.export_statistics import ExportHistory
from custom_components.electricity_pro.export_tracker import ExportTracker
from tests.test_export_ledger import interval, ledger_at
from tests.test_export_observation import START, CHANGE


@pytest.mark.parametrize("rate", ["0.50", "-0.20", "0"])
def test_legacy_checkpoint_roundtrip_keeps_replay_and_closing_publication(rate):
    ledger = ledger_at()
    ledger.record(interval(rate=rate), 0)
    history = ExportHistory(ledger.timezone, START, monthly=False)
    history.update(ledger.today)
    closed = history.checkpoint
    ledger.advance(START + timedelta(days=1))
    history.update(ledger.today)
    # These are the original ledger/history serializers, unchanged by extraction.
    checkpoint = json.loads(
        json.dumps(
            {
                "export_ledger": ledger.as_dict(),
                "export_statistics": {"today": history.as_list()},
            }
        )
    )
    tracker = ExportTracker(ledger.timezone, lambda: CHANGE)
    assert tracker.restore(checkpoint, source_configured=False) == ()
    assert tracker.as_dict() == checkpoint
    assert not tracker.ledger.record(interval(rate=rate), 0)
    assert tracker.recorded_statistics["today"] == closed
    publications = []
    saves = []
    tracker.confirm_saved(
        checkpoint,
        publish=lambda: publications.append(dict(tracker.recorded_statistics)),
        schedule_save=saves.append,
    )
    assert publications == []
    assert saves == [True]
    assert tracker.recorded_statistics["today"] == closed
    next_checkpoint = tracker.as_dict()
    assert len(next_checkpoint["export_statistics"]["today"]) == 1
    tracker.confirm_saved(
        next_checkpoint,
        publish=lambda: publications.append(dict(tracker.recorded_statistics)),
        schedule_save=saves.append,
    )
    assert publications[0]["today"].amount is None
    assert publications[0]["today"].last_reset > closed.last_reset
    assert saves == [True]
