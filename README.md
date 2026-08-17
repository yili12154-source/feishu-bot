# 飞书天气机器人

定时推送 + 交互式查询，电脑关机也能正常运行。

## 功能

### 一、定时推送（GitHub Actions）

| 推送类型 | 北京时间 | 内容 |
|---------|---------|------|
| 早推天气 | 每天 08:00 | 当日全天天气预报（@所有人） |
| 充电提醒 | 每天 17:40 | 提醒给手机/电脑/耳机充电（@所有人） |
| 下班天气 | 每天 18:55 | 当前天气+晚间趋势+出行建议（@所有人） |
| 晚推天气 | 每天 23:00 | 次日全天天气预报（@所有人） |

所有推送都会自动判断**中国法定工作日**（含调休），非工作日自动跳过。

### 二、交互式查询（Vercel Serverless）

群里 @机器人 发送关键词即可查询：

| 关键词 | 回复内容 |
|--------|---------|
| `天气` | 今日成都天气 |
| `明天天气` | 明日成都天气 |
| `充电` | 充电提醒 |
| `帮助` | 查看所有指令 |

---

## 第一部分：定时推送部署

### 1. 创建 GitHub 仓库并上传文件

### 2. 配置飞书自定义机器人 Webhook

- 在飞书群中添加「自定义机器人」
- 安全设置选「自定义关键词」，添加 `天气` 或 `成都` 或 `打卡`
- 复制 Webhook 地址

### 3. 配置 GitHub Secrets

- 仓库 → Settings → Secrets and variables → Actions → New repository secret
- Name: `FEISHU_WEBHOOK`，Secret: 你的 Webhook 地址

### 4. 启用并测试 GitHub Actions

- Actions → Feishu Push Bot → Run workflow → 选类型 → 运行

---

## 第二部分：交互式查询部署

### 1. 创建飞书企业自建应用

1. 打开 [飞书开放平台](https://open.feishu.cn/app) → 创建企业自建应用
2. 应用名称随便填（如「天气小助手」），创建后进入应用详情
3. 左侧「凭证与基础信息」→ 复制 **App ID** 和 **App Secret**
4. 左侧「添加应用能力」→ 添加「机器人」
5. 左侧「权限管理」→ 搜索并开通以下权限：
   - `im:message`（获取与发送单聊、群组消息）
   - `im:message:send_as_bot`（以应用身份发消息）
6. 左侧「版本管理与发布」→ 创建版本 → 提交发布（企业管理员审核通过后可用）
7. 把机器人添加到目标飞书群

### 2. 部署到 Vercel

1. 打开 [Vercel](https://vercel.com) → 用 GitHub 账号登录
2. 点击「Add New...」→「Project」→ 导入你的 `feishu-bot` 仓库
3. Framework Preset 选「Other」，点击「Deploy」
4. 部署完成后，复制分配的域名（如 `https://feishu-bot-xxx.vercel.app`）

### 3. 配置 Vercel 环境变量

1. Vercel 项目 → Settings → Environment Variables
2. 添加以下变量：
   - `FEISHU_APP_ID` = 你的 App ID
   - `FEISHU_APP_SECRET` = 你的 App Secret
   - `FEISHU_VERIFICATION_TOKEN` = 飞书应用「事件订阅」页面的 Verification Token（可选，建议配置）
3. 添加后重新部署（Deployments → 最新部署 → ⋯ → Redeploy）

### 4. 配置飞书事件订阅

1. 飞书开放平台 → 你的应用 → 左侧「事件订阅」
2. 请求地址填：`https://你的域名.vercel.app/api/webhook`
3. 点击「保存」，飞书会发送验证请求，配置正确会显示「验证成功」
4. 下方「添加事件」→ 搜索并添加「接收消息 v2.0」（`im.message.receive_v1`）
5. 保存后重新发布应用版本

### 5. 获取机器人 Open ID（可选但推荐）

1. 飞书群里 @机器人 随便发一条消息
2. 在 Vercel 项目 → Logs 里找到日志，复制 `event.sender.sender_id.open_id` 或 `event.message.mentions[0].id.open_id`
3. 把这个值添加到 Vercel 环境变量 `FEISHU_BOT_OPEN_ID`
4. 重新部署

这样机器人只会在被@时回复，不会响应群里其他人的对话。

### 6. 测试

在飞书群里 @机器人 发送「天气」，应该会收到今日天气回复。

---

## 数据来源

- 天气数据：[Open-Meteo](https://open-meteo.com/)（免费，无需 API Key）
- 工作日判断：[apihubs.cn 节假日 API](https://api.apihubs.cn/)
- 地点：四川省成都市博雅城市广场A座（经纬度 30.5728, 104.0668）

## 注意事项

- GitHub Actions 定时任务可能有 1-10 分钟延迟，属正常现象
- Vercel 免费版 Serverless 函数每次执行最长 10 秒，本应用足够
- 飞书企业自建应用需要企业管理员审核发布
- 交互式机器人和定时推送是两套独立系统，可以同时使用
