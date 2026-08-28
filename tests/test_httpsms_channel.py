# -*- coding: utf-8 -*-
"""Tests for the httpSMS channel (read-only SMS gateway access)."""

import json
import urllib.error
import urllib.request

import pytest

from agent_reach.channels.httpsms import HttpSMSAuthError, HttpSMSChannel, HttpSMSError
from agent_reach.config import Config


class _FakeResponse:
    def __init__(self, payload):
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self._body


def _fake_api(monkeypatch, *payloads):
    """Serve *payloads* in order and record every Request that was sent."""
    sent = []
    queue = list(payloads)

    def fake_urlopen(req, timeout=None):
        sent.append(req)
        payload = queue.pop(0) if queue else {"status": "success", "data": []}
        if isinstance(payload, Exception):
            raise payload
        return _FakeResponse(payload)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return sent


def _config(tmp_path, monkeypatch, key="test-api-key", base=None):
    monkeypatch.delenv("HTTPSMS_API_KEY", raising=False)
    monkeypatch.delenv("HTTPSMS_API_BASE", raising=False)
    config = Config(config_path=tmp_path / "config.yaml")
    if key:
        config.set("httpsms_api_key", key)
    if base:
        config.set("httpsms_api_base", base)
    return config


def _envelope(data):
    return {"status": "success", "message": "Request handled successfully", "data": data}


_PHONE = {
    "id": "32343a19-da5e-4b1b-a767-3298a73703cb",
    "phone_number": "+18005550199",
    "sim": "DEFAULT",
    "messages_per_minute": 3,
    "max_send_attempts": 2,
    "updated_at": "2026-06-05T14:26:10.303278+03:00",
}

_MESSAGE = {
    "id": "153554b5-ae44-44a0-8f4f-7bbac5657ad4",
    "type": "mobile-originated",
    "owner": "+18005550199",
    "contact": "+18005550100",
    "content": "Your verification code is 123456",
    "status": "received",
    "encrypted": False,
    "order_timestamp": "2026-06-05T14:26:09.527976+03:00",
    "received_at": "2026-06-05T14:26:09.527976+03:00",
    "sent_at": None,
    "failure_reason": None,
}

_THREAD = {
    "id": "32343a19-da5e-4b1b-a767-3298a73703ca",
    "owner": "+18005550199",
    "contact": "+18005550100",
    "last_message_content": "Your verification code is 123456",
    "last_message_id": "153554b5-ae44-44a0-8f4f-7bbac5657ad4",
    "status": "received",
    "is_read": False,
    "is_archived": False,
    "order_timestamp": "2026-06-05T14:26:09.527976+03:00",
}


def _query(req) -> dict:
    from urllib.parse import parse_qs, urlparse

    return {k: v[0] for k, v in parse_qs(urlparse(req.full_url).query).items()}


class TestHttpSMSRouting:
    def test_can_handle_httpsms_urls(self):
        ch = HttpSMSChannel()
        assert ch.can_handle("https://httpsms.com/threads")
        assert ch.can_handle("https://api.httpsms.com/v1/messages")
        assert not ch.can_handle("https://github.com/NdoleStudio/httpsms")
        assert not ch.can_handle("https://nothttpsms.com/threads")


class TestHttpSMSCheck:
    def test_off_without_api_key(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch, key=None)
        ch = HttpSMSChannel()
        status, msg = ch.check(config)
        assert status == "off"
        assert "configure httpsms-key" in msg
        assert ch.active_backend is None

    def test_ok_when_phone_registered(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_PHONE]))
        ch = HttpSMSChannel()
        status, msg = ch.check(config)
        assert status == "ok"
        assert "+18005550199" in msg
        assert ch.active_backend == "httpSMS API"
        assert sent[0].get_header("X-api-key") == "test-api-key"

    def test_warn_when_no_phone_registered(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        _fake_api(monkeypatch, _envelope([]))
        ch = HttpSMSChannel()
        status, msg = ch.check(config)
        assert status == "warn"
        assert "还没有注册的手机号" in msg

    def test_error_when_key_rejected(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        _fake_api(
            monkeypatch,
            urllib.error.HTTPError("url", 401, "Unauthorized", {}, None),
        )
        ch = HttpSMSChannel()
        status, msg = ch.check(config)
        assert status == "error"
        assert "API Key 无效" in msg
        assert ch.active_backend is None

    def test_warn_when_api_unreachable(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        _fake_api(monkeypatch, urllib.error.URLError("connection refused"))
        ch = HttpSMSChannel()
        status, msg = ch.check(config)
        assert status == "warn"
        assert "请求失败" in msg
        assert ch.active_backend is None


class TestHttpSMSReads:
    def test_list_phones_clamps_limit_and_normalizes(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_PHONE]))
        phones = HttpSMSChannel().list_phones(limit=100, config=config)
        assert phones == [
            {
                "id": _PHONE["id"],
                "phone_number": "+18005550199",
                "sim": "DEFAULT",
                "messages_per_minute": 3,
                "max_send_attempts": 2,
                "updated_at": _PHONE["updated_at"],
            }
        ]
        # 上游 validator 的上限是 20，超出会被 422 拒绝
        assert _query(sent[0])["limit"] == "20"

    def test_list_threads_defaults_owner_to_first_phone(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_PHONE]), _envelope([_THREAD]))
        threads = HttpSMSChannel().list_threads(config=config)
        assert threads[0]["contact"] == "+18005550100"
        assert threads[0]["timestamp"] == _THREAD["order_timestamp"]
        params = _query(sent[1])
        assert params["owner"] == "+18005550199"
        assert params["is_archived"] == "false"
        assert "/message-threads?" in sent[1].full_url

    def test_get_messages_maps_direction_and_query(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_MESSAGE]))
        messages = HttpSMSChannel().get_messages(
            "+18005550100", owner="+18005550199", query="verification", config=config
        )
        assert messages[0]["direction"] == "received"
        assert messages[0]["content"] == "Your verification code is 123456"
        assert messages[0]["failure_reason"] == ""
        params = _query(sent[0])
        assert params == {
            "owner": "+18005550199",
            "contact": "+18005550100",
            "limit": "20",
            "skip": "0",
            "query": "verification",
        }

    def test_outgoing_message_direction_is_sent(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        outgoing = dict(_MESSAGE, type="mobile-terminated", status="sent")
        _fake_api(monkeypatch, _envelope([outgoing]))
        messages = HttpSMSChannel().get_messages(
            "+18005550100", owner="+18005550199", config=config
        )
        assert messages[0]["direction"] == "sent"

    def test_get_message_by_id(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope(_MESSAGE))
        message = HttpSMSChannel().get_message(_MESSAGE["id"], config=config)
        assert message["id"] == _MESSAGE["id"]
        assert sent[0].full_url.endswith(f"/messages/{_MESSAGE['id']}")

    def test_search_without_contact_hits_threads(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_PHONE]), _envelope([_THREAD]))
        results = HttpSMSChannel().search("code", config=config)
        assert results[0]["last_message_content"] == _THREAD["last_message_content"]
        assert "/message-threads?" in sent[1].full_url
        assert _query(sent[1])["query"] == "code"

    def test_search_with_contact_hits_messages(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        sent = _fake_api(monkeypatch, _envelope([_MESSAGE]))
        results = HttpSMSChannel().search(
            "123456", owner="+18005550199", contact="+18005550100", config=config
        )
        assert results[0]["id"] == _MESSAGE["id"]
        assert "/messages?" in sent[0].full_url

    def test_self_hosted_api_base_is_honored(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch, base="https://sms.example.com/v1/")
        sent = _fake_api(monkeypatch, _envelope([_PHONE]))
        HttpSMSChannel().list_phones(config=config)
        assert sent[0].full_url.startswith("https://sms.example.com/v1/phones?")

    def test_missing_key_raises_auth_error(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch, key=None)
        with pytest.raises(HttpSMSAuthError):
            HttpSMSChannel().list_phones(config=config)

    def test_default_owner_errors_without_registered_phone(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        _fake_api(monkeypatch, _envelope([]))
        with pytest.raises(HttpSMSError, match="没有注册的手机号"):
            HttpSMSChannel().default_owner(config=config)

    def test_server_error_surfaces_status_code(self, tmp_path, monkeypatch):
        config = _config(tmp_path, monkeypatch)
        _fake_api(
            monkeypatch,
            urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None),
        )
        with pytest.raises(HttpSMSError, match="HTTP 500"):
            HttpSMSChannel().list_phones(config=config)
