# 飞书定时推送机器人

基于 GitHub Actions 的飞书群定时推送工具，电脑关机也能正常运行。

## 功能

| 推送类型 | 北京时间 | 内容 |
|---------|---------|------|
| 早推天气 | 每天 08:00 | 当日全天天气预报（@所有人） |
| 充电提醒 | 每天 17:40 | 提醒给手机/电脑/耳机充电（@所有人） |
| 下班天气 | 每天 18:55 | 当前天气+晚间趋势+出行建议（@所有人） |
| 晚推天气 | 每天 23:00 | 次日全天天气预报（@所有人） |

所有推送都会自动判断**中国法定工作日**（含调休），非工作日自动跳过。

## 部署步骤

### 1. 创建 GitHub 仓库

- 在 GitHub 新建一个仓库（公开或私有均可）
- 将本项目所有文件上传到仓库

### 2. 配置飞书 Webhook

- 在飞书群中添加「自定义机器人」
- 安全设置建议选「自定义关键词」，添加关键词 `天气` 或 `成都` 或 `打卡`
- 复制 Webhook 地址（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx`）

### 3. 配置 GitHub Secrets

- 进入仓库 → Settings → Secrets and variables → Actions
- 点击「New repository secret」
- Name 填 `FEISHU_WEBHOOK`
- Secret 填你的飞书机器人 Webhook 地址
- 点击「Add secret」保存

### 4. 启用 GitHub Actions

- 进入仓库的 Actions 标签页
- 如果提示禁用，点击「I understand my workflows, go ahead and enable them」
- 之后定时任务会自动运行

### 5. 手动测试

- 进入 Actions → 左侧选择「Feishu Push Bot」→ 点击「Run workflow」
- 选择推送类型（morning/charging/evening/night）
- 点击运行，查看飞书群是否收到消息

## 数据来源

- 天气数据：[Open-Meteo](https://open-meteo.com/)（免费，无需 API Key）
- 工作日判断：[timor.tech 节假日 API](https://timor.tech/api/holiday)
- 地点：四川省成都市博雅城市广场A座（经纬度 30.5728, 104.0668）

## 注意事项

- GitHub Actions 的定时任务可能有 **1-10 分钟延迟**，属于正常现象
- 公开仓库 Actions 免费无限时长；私有仓库每月 2000 分钟免费额度
- 如果推送失败（code=19021），说明飞书机器人关键词校验未通过，请在机器人安全设置中添加关键词 `天气` 或 `成都`
- 如需修改推送时间，编辑 `.github/workflows/push.yml` 中的 cron 表达式（注意是 UTC 时间，北京时间 = UTC + 8）

## 修改地点

编辑 `push.py` 中的以下变量：
```python
CHENGDU_LAT = 30.5728    # 纬度
CHENGDU_LON = 104.0668   # 经度
LOCATION_NAME = "成都市博雅城市广场A座"  # 显示名称
```
