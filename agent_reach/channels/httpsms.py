# -*- coding: utf-8 -*-
"""httpSMS — 读取自己手机上的短信（把 Android 手机当短信网关）。

上游项目：https://github.com/NdoleStudio/httpsms （MIT，Go API + Kotlin App）。
手机装上 App 后，收发的短信会同步到 httpSMS 服务端；官方 API 在
https://api.httpsms.com/v1，用 `x-api-key` 请求头鉴权。自建实例把配置项
`httpsms_api_base` 指向自己的地址即可，其余逻辑完全一致。

本渠道只做「读」：列网关手机号、列会话、读某个会话的短信、按 ID 取单条。
发短信是写操作（真会发出去、可能产生资费），不在 Agent Reach 的能力边界内 ——
需要时直接调上游的 `POST /v1/messages/send`。

配置键（~/.agent-reach/config.yaml，或同名大写环境变量）：
  httpsms_api_key   必填，在 https://httpsms.com/settings 复制
  httpsms_api_base  选填，自建实例 API 根地址，默认 https://api.httpsms.com/v1
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from .base import Channel

_UA = "agent-reach/1.0"
_TIMEOUT = 15
_DEFAULT_API_BASE = "https://api.httpsms.com/v1"

#: 上游 validator 对所有列表端点都限制 limit ∈ [1, 20]，超出直接 422
_MAX_LIMIT = 20

#: entities.MessageType → 人类可读方向（见上游 pkg/entities/message.go）
_DIRECTIONS = {
    "mobile-terminated": "sent",        # 由网关手机发出去的短信
    "mobile-originated": "received",    # 网关手机收到的短信
    "call/missed": "missed-call",       # 未接来电事件
}

_SETUP_HINT = (
    "需要 httpSMS API Key（用自己的 Android 手机当短信网关）：\n"
    "  1. 手机装 App：https://apk.httpsms.com/HttpSms.apk，登录后授予短信权限\n"
    "  2. 在 https://httpsms.com/settings 复制 API Key\n"
    "  3. agent-reach configure httpsms-key <API_KEY>\n"
    "  自建实例另需：agent-reach configure httpsms-api-base https://your-host/v1"
)


class HttpSMSError(RuntimeError):
    """httpSMS API 调用失败（网络异常或服务端报错）。"""


class HttpSMSAuthError(HttpSMSError):
    """API Key 缺失、无效或已轮换。"""


def _resolve_config(config=None):
    """Return the given config, or load the default one lazily."""
    if config is not None:
        return config
    from agent_reach.config import Config

    return Config()


def _clamp_limit(limit: int) -> int:
    """上游对 limit 的取值范围是 [1, 20]，越界会被 422 拒绝。"""
    try:
        limit = int(limit)
    except (TypeError, ValueError):
        return _MAX_LIMIT
    return max(1, min(limit, _MAX_LIMIT))


def _http_error(exc: urllib.error.HTTPError) -> HttpSMSError:
    """Translate an HTTP error into an actionable Agent Reach error."""
    try:
        body = exc.read().decode("utf-8", errors="replace")[:200]
    except Exception:  # noqa: BLE001 — body is best-effort context only
        body = ""
    if exc.code in (401, 403):
        return HttpSMSAuthError(
            f"httpSMS API Key 无效或已轮换（HTTP {exc.code}）。"
            f"到 https://httpsms.com/settings 重新复制，再跑："
            f"\n  agent-reach configure httpsms-key <API_KEY>"
        )
    return HttpSMSError(f"httpSMS API 返回 HTTP {exc.code}{('：' + body) if body else ''}")


class HttpSMSChannel(Channel):
    name = "httpsms"
    description = "httpSMS 短信（自己的 Android 手机当网关）"
    backends = ["httpSMS API"]
    tier = 2  # 需要手机装 App + API Key

    # ------------------------------------------------------------------ #
    # URL routing
    # ------------------------------------------------------------------ #

    def can_handle(self, url: str) -> bool:
        d = urllib.parse.urlparse(url).netloc.lower()
        return d == "httpsms.com" or d.endswith(".httpsms.com")

    # ------------------------------------------------------------------ #
    # HTTP plumbing
    # ------------------------------------------------------------------ #

    def _api_base(self, config=None) -> str:
        base = _resolve_config(config).get("httpsms_api_base") or _DEFAULT_API_BASE
        return str(base).rstrip("/")

    def _api_key(self, config=None) -> Optional[str]:
        return _resolve_config(config).get("httpsms_api_key")

    def _get(self, path: str, params: Optional[dict] = None, config=None) -> Any:
        """GET *path* on the httpSMS API and return the unwrapped `data` field."""
        config = _resolve_config(config)
        key = self._api_key(config)
        if not key:
            raise HttpSMSAuthError(_SETUP_HINT)

        url = f"{self._api_base(config)}{path}"
        query = {k: v for k, v in (params or {}).items() if v not in (None, "")}
        if query:
            url += "?" + urllib.parse.urlencode(query)

        req = urllib.request.Request(
            url,
            headers={
                "x-api-key": key,
                "User-Agent": _UA,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise _http_error(e) from e
        except Exception as e:  # URLError, timeout, malformed JSON…
            raise HttpSMSError(f"httpSMS API 请求失败：{e}") from e

        # 所有端点都是 {status, message, data} 信封
        return payload.get("data") if isinstance(payload, dict) else payload

    # ------------------------------------------------------------------ #
    # Normalizers — 上游字段很多，这里只留 Agent 用得上的
    # ------------------------------------------------------------------ #

    @staticmethod
    def _phone(raw: dict) -> dict:
        return {
            "id": raw.get("id", ""),
            "phone_number": raw.get("phone_number", ""),
            "sim": raw.get("sim") or "DEFAULT",
            "messages_per_minute": raw.get("messages_per_minute", 0),
            "max_send_attempts": raw.get("max_send_attempts", 0),
            "updated_at": raw.get("updated_at", ""),
        }

    @staticmethod
    def _thread(raw: dict) -> dict:
        return {
            "id": raw.get("id", ""),
            "owner": raw.get("owner", ""),
            "contact": raw.get("contact", ""),
            "last_message_content": raw.get("last_message_content", ""),
            "last_message_id": raw.get("last_message_id", ""),
            "status": raw.get("status", ""),
            "is_read": raw.get("is_read", False),
            "is_archived": raw.get("is_archived", False),
            "timestamp": raw.get("order_timestamp", ""),
        }

    @staticmethod
    def _message(raw: dict) -> dict:
        msg_type = raw.get("type", "")
        return {
            "id": raw.get("id", ""),
            "direction": _DIRECTIONS.get(msg_type, msg_type),
            "owner": raw.get("owner", ""),
            "contact": raw.get("contact", ""),
            "content": raw.get("content", ""),
            "status": raw.get("status", ""),
            "encrypted": raw.get("encrypted", False),
            "timestamp": raw.get("order_timestamp", ""),
            "received_at": raw.get("received_at") or "",
            "sent_at": raw.get("sent_at") or "",
            "failure_reason": raw.get("failure_reason") or "",
        }

    # ------------------------------------------------------------------ #
    # Health check
    # ------------------------------------------------------------------ #

    def check(self, config=None):
        self.active_backend = None
        config = _resolve_config(config)

        if not self._api_key(config):
            return "off", _SETUP_HINT

        try:
            phones = self.list_phones(limit=_MAX_LIMIT, config=config)
        except HttpSMSAuthError as e:
            return "error", str(e)
        except HttpSMSError as e:
            return "warn", f"API Key 已配置，但 {e}"

        self.active_backend = self.backends[0]
        if not phones:
            return "warn", (
                "API Key 可用，但账号下还没有注册的手机号。"
                "在手机上装 https://apk.httpsms.com/HttpSms.apk 并登录同一账号即可"
            )
        numbers = "、".join(p["phone_number"] for p in phones if p.get("phone_number"))
        return "ok", f"短信收件箱可读（网关手机号：{numbers}）"

    # ------------------------------------------------------------------ #
    # Data-fetching methods
    # ------------------------------------------------------------------ #

    def list_phones(self, limit: int = 20, query: Optional[str] = None, config=None) -> list:
        """列出账号下注册的网关手机号。

        Returns a list of dicts with keys:
          id, phone_number, sim, messages_per_minute, max_send_attempts, updated_at
        """
        data = self._get(
            "/phones",
            {"limit": _clamp_limit(limit), "skip": 0, "query": query},
            config,
        )
        return [self._phone(p) for p in (data or [])]

    def default_owner(self, config=None) -> str:
        """取第一个注册的网关手机号，作为 owner 参数的默认值。"""
        phones = self.list_phones(limit=1, config=config)
        if not phones or not phones[0].get("phone_number"):
            raise HttpSMSError(
                "账号下没有注册的手机号，先在手机上装 httpSMS App 并登录同一账号"
            )
        return phones[0]["phone_number"]

    def list_threads(
        self,
        owner: Optional[str] = None,
        limit: int = 20,
        query: Optional[str] = None,
        skip: int = 0,
        archived: bool = False,
        config=None,
    ) -> list:
        """列出某个网关手机号的短信会话（按时间倒序）。

        Args:
            owner:    网关手机号，如 "+18005550199"；省略则用第一个注册的手机号
            limit:    最多返回条数（上游上限 20）
            query:    模糊过滤，匹配最后一条内容 / 双方号码
            archived: True 时只看已归档会话

        Returns a list of dicts with keys:
          id, owner, contact, last_message_content, last_message_id,
          status, is_read, is_archived, timestamp
        """
        config = _resolve_config(config)
        owner = owner or self.default_owner(config)
        data = self._get(
            "/message-threads",
            {
                "owner": owner,
                "limit": _clamp_limit(limit),
                "skip": max(0, int(skip)),
                "query": query,
                "is_archived": "true" if archived else "false",
            },
            config,
        )
        return [self._thread(t) for t in (data or [])]

    def get_messages(
        self,
        contact: str,
        owner: Optional[str] = None,
        limit: int = 20,
        query: Optional[str] = None,
        skip: int = 0,
        config=None,
    ) -> list:
        """读某个联系人的短信往来（按时间倒序，最新在前）。

        Args:
            contact: 对方号码，如 "+18005550100"
            owner:   网关手机号；省略则用第一个注册的手机号
            limit:   最多返回条数（上游上限 20）
            query:   只保留内容包含该关键词的短信（找验证码很好用）

        Returns a list of dicts with keys:
          id, direction (sent/received/missed-call), owner, contact, content,
          status, encrypted, timestamp, received_at, sent_at, failure_reason
        """
        config = _resolve_config(config)
        owner = owner or self.default_owner(config)
        data = self._get(
            "/messages",
            {
                "owner": owner,
                "contact": contact,
                "limit": _clamp_limit(limit),
                "skip": max(0, int(skip)),
                "query": query,
            },
            config,
        )
        return [self._message(m) for m in (data or [])]

    def get_message(self, message_id: str, config=None) -> dict:
        """按 ID 取单条短信详情。"""
        data = self._get(f"/messages/{urllib.parse.quote(str(message_id))}", None, config)
        return self._message(data or {})

    def search(
        self,
        query: str,
        owner: Optional[str] = None,
        contact: Optional[str] = None,
        limit: int = 20,
        config=None,
    ) -> list:
        """搜索短信。

        给了 contact 就在该会话内按内容搜（返回短信列表）；没给就在会话列表里搜
        （匹配最后一条内容和双方号码，返回会话列表，再用 get_messages 展开）。

        注意：上游的全量搜索端点 `/messages/search` 要求 Cloudflare Turnstile
        token，只有网页端能用，所以这里走 owner/contact 维度的过滤。
        """
        config = _resolve_config(config)
        owner = owner or self.default_owner(config)
        if contact:
            return self.get_messages(
                contact, owner=owner, limit=limit, query=query, config=config
            )
        return self.list_threads(owner=owner, limit=limit, query=query, config=config)
