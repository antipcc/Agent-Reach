# httpSMS 配置指南

## 功能说明
[httpSMS](https://github.com/NdoleStudio/httpsms)（MIT）把你自己的 Android 手机变成短信网关：
手机装上 App 之后，手机收发的短信会同步到 httpSMS 服务端，Agent 通过 HTTP API 就能读到。
配置后解锁：

- 列出账号下注册的网关手机号
- 列出短信会话（按时间倒序）
- 读某个联系人的完整短信往来
- 在会话内按关键词过滤（找验证码最常用）

**只读。** Agent Reach 不提供发短信能力——发短信是写操作、会真的发出去并可能产生资费，
需要时由你自己调上游的 `POST /v1/messages/send`。

## 需要用户手动做的步骤

**三步，都在手机和浏览器里完成：**

### 1. 手机装 App（Android）
下载安装 https://apk.httpsms.com/HttpSms.apk

### 2. 登录并授权
打开 App，用和网页端相同的账号登录，按提示授予短信权限，并把 App 加入电池优化白名单
（否则系统会杀后台，短信同步会断）。

### 3. 复制 API Key
打开 https://httpsms.com/settings，复制 API Key 交给 Agent。

## Agent 可自动完成的步骤

```bash
# 保存 API Key（写入 ~/.agent-reach/config.yaml，权限 600）
agent-reach configure httpsms-key <API_KEY>

# 自建实例才需要（默认是官方 https://api.httpsms.com/v1）
agent-reach configure httpsms-api-base https://your-host/v1

# 验证
agent-reach doctor --json
```

`configure httpsms-key` 会顺手调一次 API 验活，直接告诉你 Key 有没有效、网关手机号是哪个。

## 验证

```bash
# 列出网关手机号
curl -s "https://api.httpsms.com/v1/phones?limit=20&skip=0" -H "x-api-key: $HTTPSMS_API_KEY"
```

或者用 Python：

```python
from agent_reach.channels.httpsms import HttpSMSChannel

ch = HttpSMSChannel()
print(ch.list_phones())                      # 网关手机号
print(ch.list_threads())                     # 最近会话
print(ch.get_messages("+18005550100"))       # 某个联系人的短信
```

## 常见问题

**Q: 要花钱吗？**
A: 官方托管服务（httpsms.com）有免费额度和付费套餐，具体看 https://httpsms.com/pricing。
上游是 MIT 开源的，也可以按 [上游 README](https://github.com/NdoleStudio/httpsms#self-host-setup---docker)
用 Docker 完全自建，然后用 `configure httpsms-api-base` 指过去。

**Q: 读到的短信是乱码 / 密文？**
A: 你在 App 里开了端到端加密。开了加密之后服务端只存密文，API 读到的 `content` 就是密文
（返回里 `encrypted: true`），密钥只在手机上，Agent 解不开。要让 Agent 读短信就别开加密，
或者自己在本地解密。

**Q: doctor 显示 API Key 可用，但读不到最新短信？**
A: 手机端 App 没在后台跑。检查：App 是否登录同一账号、短信权限是否授予、是否加入电池优化白名单。
在 https://httpsms.com 网页端能看到手机的心跳（heartbeat）状态。

**Q: 为什么一次最多只能取 20 条？**
A: 上游 API 对所有列表端点的 `limit` 校验就是 `[1, 20]`，超过直接 422。要往前翻用 `skip` 分页。

**Q: 能全局搜索所有短信吗？**
A: 上游的全量搜索端点 `/messages/search` 需要 Cloudflare Turnstile token，只有网页端能用。
所以这里的搜索是「会话维度」的：不给 contact 就在会话列表里搜（匹配最后一条内容和号码），
给了 contact 就在该会话内按内容搜。

**Q: 安全性？**
A: API Key 只存在本机 `~/.agent-reach/config.yaml`（权限 600），不上传不外传。
短信里常有验证码和隐私内容，别把 Key 共享给别人，也别在多人共用的机器上配。
