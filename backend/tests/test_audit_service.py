"""
Tests for backend/services/audit_service.py — log_action and get_audit_logs.
"""

import json

import pytest


class TestLogAction:
    """Tests for audit_service.log_action."""

    def test_inserts_row_and_returns_audit_id(self, app, db_conn):
        """log_action should insert a row and return a positive audit_id."""
        with app.app_context():
            from services.audit_service import log_action

            audit_id = log_action(
                actor="admin",
                action="user_create",
                target="new_user",
                details={"role": "patient"},
                ip="127.0.0.1",
            )

        assert isinstance(audit_id, int)
        assert audit_id > 0

        row = db_conn.execute(
            "SELECT * FROM audit_log WHERE audit_id = ?", (audit_id,)
        ).fetchone()
        assert row is not None
        assert row["actor"] == "admin"
        assert row["action"] == "user_create"
        assert row["target"] == "new_user"
        assert json.loads(row["details"]) == {"role": "patient"}
        assert row["ip_address"] == "127.0.0.1"
        assert row["timestamp"] is not None

    def test_optional_fields_default_to_none(self, app, db_conn):
        """target, details, and ip should be nullable."""
        with app.app_context():
            from services.audit_service import log_action

            audit_id = log_action(actor="system", action="startup")

        row = db_conn.execute(
            "SELECT * FROM audit_log WHERE audit_id = ?", (audit_id,)
        ).fetchone()
        assert row["target"] is None
        assert row["details"] is None
        assert row["ip_address"] is None

    def test_details_serialized_as_json(self, app, db_conn):
        """details dict should be stored as a JSON string."""
        with app.app_context():
            from services.audit_service import log_action

            details = {"key": "value", "nested": {"a": 1}}
            audit_id = log_action(
                actor="admin", action="test", details=details
            )

        row = db_conn.execute(
            "SELECT details FROM audit_log WHERE audit_id = ?", (audit_id,)
        ).fetchone()
        assert json.loads(row["details"]) == details


class TestGetAuditLogs:
    """Tests for audit_service.get_audit_logs."""

    def _seed_logs(self, app, count=5):
        """Insert multiple audit log entries for testing."""
        with app.app_context():
            from services.audit_service import log_action

            ids = []
            for i in range(count):
                actor = "admin" if i % 2 == 0 else "doctor"
                action = "login_success" if i % 3 == 0 else "user_create"
                audit_id = log_action(
                    actor=actor,
                    action=action,
                    target=f"target_{i}",
                    details={"index": i},
                    ip="10.0.0.1",
                )
                ids.append(audit_id)
            return ids

    def test_returns_paginated_results(self, app):
        """get_audit_logs should return paginated results."""
        self._seed_logs(app, count=5)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs(page=1, per_page=3)

        assert result["total"] == 5
        assert result["page"] == 1
        assert result["per_page"] == 3
        assert len(result["logs"]) == 3

    def test_page_2_returns_remaining(self, app):
        """Second page should return remaining entries."""
        self._seed_logs(app, count=5)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs(page=2, per_page=3)

        assert len(result["logs"]) == 2

    def test_filter_by_actor(self, app):
        """Filtering by actor should return only matching entries."""
        self._seed_logs(app, count=5)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs(actor="admin")

        # indices 0, 2, 4 are "admin"
        assert result["total"] == 3
        for log in result["logs"]:
            assert log["actor"] == "admin"

    def test_filter_by_action(self, app):
        """Filtering by action should return only matching entries."""
        self._seed_logs(app, count=5)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs(action="login_success")

        # indices 0, 3 have action "login_success"
        assert result["total"] == 2
        for log in result["logs"]:
            assert log["action"] == "login_success"

    def test_filter_by_actor_and_action(self, app):
        """Combined filters should intersect."""
        self._seed_logs(app, count=5)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs(actor="admin", action="login_success")

        # index 0 is admin + login_success
        assert result["total"] == 1
        assert result["logs"][0]["actor"] == "admin"
        assert result["logs"][0]["action"] == "login_success"

    def test_empty_result(self, app):
        """Should return empty list when no logs match."""
        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs()

        assert result["total"] == 0
        assert result["logs"] == []

    def test_details_deserialized_from_json(self, app):
        """Returned logs should have details parsed from JSON."""
        with app.app_context():
            from services.audit_service import log_action, get_audit_logs

            log_action(actor="admin", action="test", details={"key": "val"})
            result = get_audit_logs()

        assert result["logs"][0]["details"] == {"key": "val"}

    def test_logs_ordered_by_most_recent_first(self, app):
        """Logs should be returned in descending order by audit_id."""
        self._seed_logs(app, count=3)

        with app.app_context():
            from services.audit_service import get_audit_logs

            result = get_audit_logs()

        ids = [log["audit_id"] for log in result["logs"]]
        assert ids == sorted(ids, reverse=True)
