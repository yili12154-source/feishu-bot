#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书定时推送脚本
支持：早推天气、充电提醒、下班天气、晚推天气
用法：python push.py <type>
  type: morning | charging | evening | night
"""

import sys
import json
import requests
from datetime import datetime, timedelta

# ===== 配置 =====
FEISHU_WEBHOOK = ""  # 从环境变量 FEISHU_WEBHOOK 读取
CHENGDU_LAT = 30.5728
CHENGDU_LON = 104.0668
LOCATION_NAME = "成都市博雅城市广场A座"

# WMO 天气代码映射
WEATHER_CODE_MAP = {
    0: "晴", 1: "大部晴朗", 2: "局部多云", 3: "阴",
    45: "雾", 48: "雾凇",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨",
    56: "冻毛毛雨", 57: "大冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨",
    66: "冻雨", 67: "大冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "阵雨", 82: "大阵雨",
    85: "小阵雪", 86: "大阵雪",
    95: "雷暴", 96: "雷暴伴小冰雹", 99: "雷暴伴大冰雹",
}


def get_webhook():
    import os
    url = os.environ.get("FEISHU_WEBHOOK", "").strip()
    if not url:
        print("错误：未设置环境变量 FEISHU_WEBHOOK")
        sys.exit(1)
    return url


def is_workday(date_str):
    """判断是否为中国法定工作日，返回 (is_workday, reason)"""
    try:
        date_int = int(date_str.replace("-", ""))
        resp = requests.get(f"https://api.apihubs.cn/holiday/get?date={date_int}", timeout=10)
        data = resp.json()
        if data.get("code") == 0 and data.get("data", {}).get("list"):
            item = data["data"]["list"][0]
            workday = item.get("workday", -1)
            holiday = item.get("holiday", -1)
            # workday: 1=工作日, 0=休息日
            if workday == 1:
                return True, "工作日"
            else:
                return False, "休息日"
    except Exception as e:
        print(f"节假日API请求失败: {e}，使用周一到周五判断")
    # 降级：周一到周五
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d.weekday() < 5, "周一至周五（降级判断）"


def fetch_weather(date_str=None):
    """查询成都天气，返回天气数据字典"""
    params = {
        "latitude": CHENGDU_LAT,
        "longitude": CHENGDU_LON,
        "daily": "weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max,windspeed_10m_max,uv_index_max",
        "current_weather": "true",
        "timezone": "Asia/Shanghai",
        "forecast_days": 2,
    }
    resp = requests.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=15)
    data = resp.json()

    daily = data.get("daily", {})
    current = data.get("current_weather", {})

    # 确定取哪一天的数据
    dates = daily.get("time", [])
    target_idx = 0
    if date_str and date_str in dates:
        target_idx = dates.index(date_str)
    elif date_str and len(dates) > 1 and date_str == dates[1]:
        target_idx = 1

    weather_code = daily["weathercode"][target_idx]
    weather_desc = WEATHER_CODE_MAP.get(weather_code, f"未知({weather_code})")

    return {
        "weather": weather_desc,
        "temp_max": daily["temperature_2m_max"][target_idx],
        "temp_min": daily["temperature_2m_min"][target_idx],
        "precip_prob": daily["precipitation_probability_max"][target_idx],
        "wind_speed": daily["windspeed_10m_max"][target_idx],
        "uv_index": daily["uv_index_max"][target_idx],
        "current_temp": current.get("temperature"),
        "current_wind": current.get("windspeed"),
        "current_weather": WEATHER_CODE_MAP.get(current.get("weathercode"), "未知"),
    }


def post_feishu(card):
    """推送飞书消息"""
    webhook = get_webhook()
    try:
        resp = requests.post(
            webhook,
            json=card,
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        result = resp.json()
        code = result.get("code", result.get("StatusCode", -1))
        if code == 0:
            print("推送成功")
            return True
        else:
            print(f"推送失败: {result}")
            # 关键词校验失败时重试
            if code == 19021 or "keyword" in str(result.get("msg", "")):
                print("关键词校验失败，尝试追加关键词...")
                # 在卡片备注中追加关键词
                for el in card["card"]["elements"]:
                    if el.get("tag") == "note":
                        el["elements"][0]["content"] += " · 天气打卡"
                        break
                resp2 = requests.post(webhook, json=card, headers={"Content-Type": "application/json"}, timeout=15)
                print(f"重试结果: {resp2.json()}")
                return resp2.json().get("code", -1) == 0
            return False
    except Exception as e:
        print(f"推送异常: {e}")
        return False


def build_card(title, content_lines, color="blue", note="到点啦 · 定时推送"):
    """构建飞书interactive卡片"""
    elements = []
    for line in content_lines:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": line}
        })
    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text", "content": note}]
    })
    return {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": color
            },
            "elements": elements
        }
    }


def push_morning():
    """早推：当日天气"""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
    work, reason = is_workday(today)
    if not work:
        print(f"今天({today} {weekday})是{reason}，跳过推送")
        return

    w = fetch_weather(today)
    title = f"今日成都天气（{today[5:]} {weekday}）"
    lines = [
        f"<at user_id=\"all\">所有人</at> 早上好！今日天气如下：",
        f"**天气：** {w['weather']}",
        f"**气温：** {w['temp_min']}℃ ~ {w['temp_max']}℃（当前 {w['current_temp']}℃）",
        f"**降水概率：** {w['precip_prob']}%",
        f"**风力：** {w['wind_speed']} km/h",
        f"**紫外线：** {w['uv_index']}",
        f"**地点：** {LOCATION_NAME}",
    ]
    # 出行建议
    tips = []
    if w["precip_prob"] >= 50:
        tips.append("🌧️ 今天可能下雨，记得带伞")
    if w["temp_max"] >= 30:
        tips.append("🥵 气温较高，注意防暑降温")
    if w["temp_min"] <= 10:
        tips.append("🧥 早晚较凉，注意添衣")
    if w["uv_index"] >= 6:
        tips.append("☀️ 紫外线较强，注意防晒")
    if tips:
        lines.append("**出行建议：** " + "；".join(tips))

    card = build_card(title, lines, color="blue", note=f"{LOCATION_NAME} · 早间天气推送")
    post_feishu(card)


def push_charging():
    """充电提醒"""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
    work, reason = is_workday(today)
    if not work:
        print(f"今天({today} {weekday})是{reason}，跳过推送")
        return

    title = "🔋 充电提醒"
    lines = [
        f"<at user_id=\"all\">所有人</at> 打工人注意啦！",
        "",
        "别忘了给 **手机、电脑、耳机** 充上电～",
        "",
        "🔌 电量满格，明天不慌",
        "☕ 今晚好好休息，明天继续搬砖",
    ]
    card = build_card(title, lines, color="orange", note="到点啦 · 工作日充电提醒")
    post_feishu(card)


def push_evening():
    """下班天气：当前+晚间"""
    today = datetime.now().strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][datetime.now().weekday()]
    work, reason = is_workday(today)
    if not work:
        print(f"今天({today} {weekday})是{reason}，跳过推送")
        return

    w = fetch_weather(today)
    title = f"下班天气提醒（{today[5:]} {weekday}）"
    lines = [
        f"<at user_id=\"all\">所有人</at> 快下班啦，看看今晚天气：",
        f"**当前天气：** {w['current_weather']}，{w['current_temp']}℃",
        f"**今日气温：** {w['temp_min']}℃ ~ {w['temp_max']}℃",
        f"**晚间降水概率：** {w['precip_prob']}%",
        f"**风力：** {w['wind_speed']} km/h",
        f"**地点：** {LOCATION_NAME}",
    ]
    tips = []
    if w["precip_prob"] >= 50:
        tips.append("🌧️ 今晚可能有雨，下班记得带伞")
    else:
        tips.append("🌤️ 晚间天气尚可，放心下班")
    if w["current_temp"] <= 15:
        tips.append("🧥 晚上有点凉，加件外套")
    lines.append("**下班建议：** " + "；".join(tips))

    card = build_card(title, lines, color="turquoise", note=f"{LOCATION_NAME} · 下班天气推送")
    post_feishu(card)


def push_night():
    """晚推：次日天气"""
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][(datetime.now() + timedelta(days=1)).weekday()]
    work, reason = is_workday(tomorrow)
    if not work:
        print(f"明天({tomorrow} {weekday})是{reason}，跳过推送")
        return

    w = fetch_weather(tomorrow)
    title = f"明日成都天气（{tomorrow[5:]} {weekday}）"
    lines = [
        f"<at user_id=\"all\">所有人</at> 明天是工作日，提前看看天气：",
        f"**天气：** {w['weather']}",
        f"**气温：** {w['temp_min']}℃ ~ {w['temp_max']}℃",
        f"**降水概率：** {w['precip_prob']}%",
        f"**风力：** {w['wind_speed']} km/h",
        f"**紫外线：** {w['uv_index']}",
        f"**地点：** {LOCATION_NAME}",
    ]
    tips = []
    if w["precip_prob"] >= 50:
        tips.append("🌧️ 明天可能下雨，出门带伞")
    if w["temp_max"] >= 30:
        tips.append("🥵 明天较热，注意防暑")
    if w["temp_min"] <= 10:
        tips.append("🧥 明天早晚凉，注意添衣")
    if w["uv_index"] >= 6:
        tips.append("☀️ 紫外线强，注意防晒")
    if tips:
        lines.append("**明日建议：** " + "；".join(tips))

    card = build_card(title, lines, color="indigo", note=f"{LOCATION_NAME} · 晚间天气推送")
    post_feishu(card)


def main():
    if len(sys.argv) < 2:
        print("用法: python push.py <morning|charging|evening|night>")
        sys.exit(1)

    push_type = sys.argv[1].lower()
    print(f"执行推送类型: {push_type}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if push_type == "morning":
        push_morning()
    elif push_type == "charging":
        push_charging()
    elif push_type == "evening":
        push_evening()
    elif push_type == "night":
        push_night()
    else:
        print(f"未知类型: {push_type}")
        sys.exit(1)


if __name__ == "__main__":
    main()
