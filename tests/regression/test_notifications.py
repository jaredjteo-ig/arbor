"""Regression tests for in-app notifications service (T06 / Z10).

Pins:
- Single-row create writes the expected fields.
- Bulk engagement-pending fanout creates one row per (response, user).
- list_user_notifications respects only_unresolved + kind filter.
- mark_resolved enforces user ownership.
- mark_resolved_by_link auto-resolves notifications when a user submits
  the related survey response.
"""

from __future__ import annotations

import pytest

from hr_advisory.services import notifications


@pytest.fixture
def fake_store(monkeypatch):
    """In-memory replacement for dataflow_crud during this module."""
    store: dict[int, dict] = {}
    next_id = {"v": 1}

    def fake_create(model, fields):
        if model != "Notification":
            raise AssertionError(f"Unexpected create on {model}")
        nid = next_id["v"]
        next_id["v"] += 1
        record = {"id": nid, **fields}
        store[nid] = record
        return record

    def fake_list(model, where, **_):
        if model != "Notification":
            return []
        results = []
        for r in store.values():
            ok = True
            for k, v in where.items():
                if r.get(k) != v:
                    ok = False
                    break
            if ok:
                results.append(dict(r))
        return results

    def fake_update(model, record_id, fields):
        if model != "Notification":
            raise AssertionError(f"Unexpected update on {model}")
        # New API: record_id is int (or dict for legacy callers).
        if isinstance(record_id, dict):
            for r in store.values():
                ok = True
                for k, v in record_id.items():
                    if r.get(k) != v:
                        ok = False
                        break
                if ok:
                    r.update(fields)
                    return r
            return None
        rec = store.get(int(record_id))
        if rec is not None:
            rec.update(fields)
        return rec

    monkeypatch.setattr(
        notifications.dataflow_crud, "create", fake_create
    )
    monkeypatch.setattr(
        notifications.dataflow_crud, "list_records", fake_list
    )
    monkeypatch.setattr(
        notifications.dataflow_crud, "update", fake_update
    )
    return store


@pytest.mark.regression
def test_create_notification_writes_expected_fields(fake_store):
    record = notifications.create_notification(
        user_id=42,
        company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Pulse open",
        body="Takes 90 seconds",
        link="/my-engagement-surveys/7/respond",
        actor_user_id=10,
        metadata={"response_id": 7},
    )
    assert record["user_id"] == 42
    assert record["company_id"] == 1
    assert record["kind"] == "engagement_pending"
    assert record["title"] == "Pulse open"
    assert record["link"] == "/my-engagement-surveys/7/respond"
    assert record["actor_user_id"] == 10
    assert record["is_resolved"] is False
    assert '"response_id": 7' in record["metadata_json"]


@pytest.mark.regression
def test_create_notification_validates_inputs(fake_store):
    with pytest.raises(ValueError, match="user_id must be > 0"):
        notifications.create_notification(
            user_id=0, company_id=1, kind="x", title="t"
        )
    with pytest.raises(ValueError, match="company_id must be > 0"):
        notifications.create_notification(
            user_id=1, company_id=0, kind="x", title="t"
        )
    with pytest.raises(ValueError, match="kind must be"):
        notifications.create_notification(
            user_id=1, company_id=1, kind="", title="t"
        )
    with pytest.raises(ValueError, match="title must be"):
        notifications.create_notification(
            user_id=1, company_id=1, kind="x", title=""
        )


@pytest.mark.regression
def test_bulk_create_fanout_creates_one_per_pair(fake_store):
    pairs = [(101, 1), (102, 2), (103, 3)]
    count = notifications.bulk_create_engagement_pending(
        company_id=1,
        actor_user_id=10,
        survey_name="H1 2026 Pulse",
        closes_at_iso="2026-05-21",
        response_user_pairs=pairs,
    )
    assert count == 3
    assert len(fake_store) == 3
    rows = list(fake_store.values())
    # Each row links to its specific response.
    response_ids = sorted([
        int(r["link"].split("/")[2]) for r in rows
    ])
    assert response_ids == [101, 102, 103]
    # All point at the same survey, named correctly.
    assert all("H1 2026 Pulse" in r["title"] for r in rows)


@pytest.mark.regression
def test_list_filters_by_kind_and_unresolved(fake_store):
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Pulse 1",
    )
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Pulse 2",
    )
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_REMINDER,
        title="Reminder",
    )
    notifications.create_notification(
        user_id=99, company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Other user",
    )

    pending = notifications.list_user_notifications(
        42, kind=notifications.ENGAGEMENT_PENDING
    )
    assert len(pending) == 2
    assert all(p["kind"] == "engagement_pending" for p in pending)
    assert all(p["user_id"] == 42 for p in pending)


@pytest.mark.regression
def test_mark_resolved_succeeds_for_owner(fake_store):
    record = notifications.create_notification(
        user_id=42, company_id=1, kind="x", title="t",
    )
    ok = notifications.mark_resolved(record["id"], user_id=42)
    assert ok is True
    assert fake_store[record["id"]]["is_resolved"] is True
    assert fake_store[record["id"]]["resolved_at"] is not None


@pytest.mark.regression
def test_mark_resolved_rejects_non_owner(fake_store):
    record = notifications.create_notification(
        user_id=42, company_id=1, kind="x", title="t",
    )
    ok = notifications.mark_resolved(record["id"], user_id=99)
    assert ok is False
    assert fake_store[record["id"]]["is_resolved"] is False


@pytest.mark.regression
def test_mark_resolved_by_link_resolves_matching_rows(fake_store):
    """The engagement submit handler calls this to dismiss the pending
    card the moment a user submits — link-based resolution avoids
    needing the response_id<->notification_id mapping at submit time.
    """
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Pulse 1",
        link="/my-engagement-surveys/101/respond",
    )
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_REMINDER,
        title="Pulse 1 reminder",
        link="/my-engagement-surveys/101/respond",
    )
    notifications.create_notification(
        user_id=42, company_id=1,
        kind=notifications.ENGAGEMENT_PENDING,
        title="Other pulse",
        link="/my-engagement-surveys/102/respond",
    )

    count = notifications.mark_resolved_by_link(
        42, "/my-engagement-surveys/101/respond"
    )
    assert count == 2
    rows = notifications.list_user_notifications(42, only_unresolved=True)
    assert len(rows) == 1
    assert rows[0]["title"] == "Other pulse"
