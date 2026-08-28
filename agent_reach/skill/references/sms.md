# 短信 / SMS

httpSMS —— 用户自己的 Android 手机当短信网关，读手机上的短信（验证码、通知、会话记录）。

**只读。** 本渠道不发短信。用户要求发短信 → 告诉他这超出 Agent Reach 范围，
需要自己调上游 `POST /v1/messages/send`。

## 先决条件

需要 API Key（`httpsms_api_key`）。没配的话 `agent-reach doctor` 会显示 `httpsms` 为 off，
让用户按 [setup-httpsms 指南](https://github.com/Panniantong/agent-reach/blob/main/agent_reach/guides/setup-httpsms.md)
装手机 App 并复制 Key，然后：

```bash
agent-reach configure httpsms-key <API_KEY>
```

## Python（推荐，字段已归一化）

```python
from agent_reach.channels.httpsms import HttpSMSChannel

ch = HttpSMSChannel()

# 网关手机号（owner）
ch.list_phones()

# 最近会话（省略 owner 就用第一个注册的手机号）
ch.list_threads(limit=20)

# 某个联系人的短信往来，最新在前
ch.get_messages("+18005550100", limit=20)

# 在会话内找验证码
ch.get_messages("+18005550100", query="code", limit=5)

# 会话维度搜索（不给 contact 时匹配最后一条内容和号码）
ch.search("银行")

# 单条详情
ch.get_message("153554b5-ae44-44a0-8f4f-7bbac5657ad4")
```

返回的短信字段：`id / direction / owner / contact / content / status / encrypted /
timestamp / received_at / sent_at / failure_reason`。
`direction` 是 `sent`（手机发出去的）、`received`（手机收到的）、`missed-call`（未接来电）。

## curl（自建实例把域名换成自己的）

```bash
# 网关手机号
curl -s "https://api.httpsms.com/v1/phones?limit=20&skip=0" -H "x-api-key: $HTTPSMS_API_KEY"

# 会话列表
curl -s "https://api.httpsms.com/v1/message-threads?owner=%2B18005550199&limit=20&skip=0&is_archived=false" \
  -H "x-api-key: $HTTPSMS_API_KEY"

# 某个联系人的短信（owner/contact 里的 + 要写成 %2B）
curl -s "https://api.httpsms.com/v1/messages?owner=%2B18005550199&contact=%2B18005550100&limit=20&skip=0" \
  -H "x-api-key: $HTTPSMS_API_KEY"
```

## 注意事项

- **limit 上限是 20**：上游 validator 对所有列表端点都是 `[1, 20]`，超了返回 422。往前翻用 `skip`。
- **没有全局搜索**：上游 `/messages/search` 要 Cloudflare Turnstile token，只有网页端能用。
  搜索只能落在 owner（+ 可选 contact）维度上。
- **密文**：用户在 App 里开了端到端加密的话，`content` 是密文、`encrypted: true`，解不开。
  这时告诉用户「要让 Agent 读短信需要关掉 App 里的端到端加密」，不要硬猜内容。
- **读不到最新短信**：手机端 App 被杀后台了（电池优化 / 权限），让用户去 https://httpsms.com 看心跳状态。
- **隐私**：短信里通常有验证码和个人信息。只读用户明确要求的那个会话，不要顺手把整个收件箱倒出来，
  也不要把短信内容写进 agent workspace 的文件里。
