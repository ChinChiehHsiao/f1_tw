#!/usr/bin/env python3
"""
F1 週一通知：每週一檢查本週是否有排位賽
有 → 發送本週賽程 Flex Message 圖卡
沒有 → 發送本週無賽事圖卡，顯示下一站資訊
"""

import json, os, sys
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import URLError

JOLPICA_URL = "https://api.jolpi.ca/ergast/f1/2026.json"
LINE_API_URL = "https://api.line.me/v2/bot/message/broadcast"
SITE_URL     = "https://chinchiehhsiao.github.io/f1_tw"

TW_TZ    = timezone(timedelta(hours=8))
WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日']

RACE_META = {
    'Australian Grand Prix':    '澳洲',
    'Chinese Grand Prix':       '中國',
    'Japanese Grand Prix':      '日本',
    'Miami Grand Prix':         '邁阿密',
    'Canadian Grand Prix':      '加拿大',
    'Monaco Grand Prix':        '摩納哥',
    'Barcelona Grand Prix':     '巴塞隆納',
    'Austrian Grand Prix':      '奧地利',
    'British Grand Prix':       '英國',
    'Belgian Grand Prix':       '比利時',
    'Hungarian Grand Prix':     '匈牙利',
    'Dutch Grand Prix':         '荷蘭',
    'Italian Grand Prix':       '義大利',
    'Spanish Grand Prix':       '西班牙',
    'Azerbaijan Grand Prix':    '亞塞拜然',
    'Singapore Grand Prix':     '新加坡',
    'United States Grand Prix': '美國',
    'Mexico City Grand Prix':   '墨西哥',
    'Brazilian Grand Prix':     '巴西',
    'Las Vegas Grand Prix':     '拉斯維加斯',
    'Qatar Grand Prix':         '卡達',
    'Abu Dhabi Grand Prix':     '阿布達比',
}

def race_name(name):
    return RACE_META.get(name, name.replace(' Grand Prix', ''))

def fetch_races():
    req = Request(JOLPICA_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode('utf-8'))
            return data['MRData']['RaceTable']['Races']
    except (URLError, KeyError, json.JSONDecodeError) as e:
        print(f"[ERROR] 抓取賽程失敗: {e}", file=sys.stderr)
        return []

def load_elta():
    try:
        with open('elta.json', encoding='utf-8') as f:
            return json.load(f).get('sessions', {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def parse_dt_tw(date_str, time_str):
    if not time_str:
        time_str = '00:00:00Z'
    if not time_str.endswith('Z'):
        time_str += 'Z'
    dt_utc = datetime.fromisoformat(f"{date_str}T{time_str}".replace('Z', '+00:00'))
    return dt_utc.astimezone(TW_TZ)

def fmt_tw(dt):
    wd = WEEKDAYS[dt.weekday()]
    return f"{dt.month}/{dt.day}({wd}) {dt.strftime('%H:%M')}"

# ── Flex Message 組件 ──────────────────────────────────────

def footer():
    return {
        "type": "box",
        "layout": "vertical",
        "paddingAll": "0px",
        "contents": [
            {"type": "separator", "color": "#f0ede8"},
            {
                "type": "button",
                "action": {"type": "uri", "label": "查看完整資訊 →", "uri": SITE_URL},
                "color": "#1D9E75",
                "style": "link",
                "height": "sm"
            }
        ]
    }

def session_row(label, time_str, channel):
    row = {
        "type": "box",
        "layout": "horizontal",
        "paddingTop": "10px",
        "paddingBottom": "10px",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "flex": 1,
                "contents": [
                    {"type": "text", "text": label,    "size": "xs", "color": "#9c9a92"},
                    {"type": "text", "text": time_str, "size": "sm", "weight": "bold", "color": "#1a1a18"}
                ]
            }
        ]
    }
    if channel:
        row["contents"].append({
            "type": "box",
            "layout": "vertical",
            "justifyContent": "center",
            "alignItems": "flex-end",
            "contents": [{
                "type": "box",
                "layout": "vertical",
                "backgroundColor": "#E1F5EE",
                "cornerRadius": "20px",
                "paddingTop": "2px",
                "paddingBottom": "2px",
                "paddingStart": "8px",
                "paddingEnd": "8px",
                "contents": [{
                    "type": "text",
                    "text": channel,
                    "size": "xs",
                    "color": "#1D9E75",
                    "weight": "bold"
                }]
            }]
        })
    return [row, {"type": "separator", "color": "#f0ede8"}]

def build_race_bubble(race, elta):
    name      = race_name(race['raceName'])
    round_num = race['round']
    circuit   = race.get('Circuit', {}).get('circuitName', '')
    is_sprint = bool(race.get('Sprint'))
    title     = f"R{round_num} {name}站" + (" · 衝刺週" if is_sprint else "")

    rows = []
    for key, label in [('SprintQualifying', '衝刺排位'), ('Sprint', '衝刺賽'), ('Qualifying', '排位賽')]:
        s = race.get(key)
        if not s:
            continue
        dt = parse_dt_tw(s['date'], s['time'])
        ch = elta.get(key, {}).get('channel_name', '')
        rows.extend(session_row(label, fmt_tw(dt), ch))

    race_dt = parse_dt_tw(race['date'], race.get('time', ''))
    ch = elta.get('Race', {}).get('channel_name', '')
    rows.extend(session_row('正賽', fmt_tw(race_dt), ch))

    # 移除最後一條分隔線
    if rows and rows[-1].get('type') == 'separator':
        rows.pop()

    return f"🏎️ 本週 F1 · {title}", {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#1D9E75", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "🏎️ 本週 F1",  "color": "#ffffffcc", "size": "xs", "weight": "bold"},
                {"type": "text", "text": title,          "color": "#ffffff",   "size": "xl", "weight": "bold"},
                {"type": "text", "text": circuit,        "color": "#ffffffaa", "size": "xs"}
            ]
        },
        "body":   {"type": "box", "layout": "vertical", "paddingAll": "16px", "spacing": "none", "contents": rows},
        "footer": footer()
    }

def build_no_race_bubble(next_race, days_until, ref_dt):
    name      = race_name(next_race['raceName'])
    round_num = next_race['round']

    return f"本週無 F1 賽事 · 下一站 R{round_num} {name}站，還有 {days_until} 天", {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#E8002D", "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": "🏁 本週 F1",  "color": "#ffffffcc", "size": "xs", "weight": "bold"},
                {"type": "text", "text": "本週無賽事",   "color": "#ffffff",   "size": "xl", "weight": "bold"}
            ]
        },
        "body": {
            "type": "box", "layout": "vertical", "paddingAll": "16px", "spacing": "sm",
            "contents": [
                {"type": "text", "text": "下一站",               "size": "xs", "color": "#9c9a92"},
                {"type": "text", "text": f"R{round_num} {name}站", "size": "lg", "weight": "bold", "color": "#1a1a18"},
                {
                    "type": "box", "layout": "vertical",
                    "backgroundColor": "#f5f4f0", "cornerRadius": "8px",
                    "paddingAll": "12px", "margin": "md",
                    "contents": [
                        {
                            "type": "box", "layout": "horizontal",
                            "contents": [
                                {"type": "text", "text": str(days_until), "size": "3xl", "weight": "bold", "color": "#1a1a18", "flex": 0},
                                {"type": "text", "text": " 天後排位賽",   "size": "sm",  "color": "#5F5E5A", "gravity": "bottom"}
                            ]
                        },
                        {"type": "text", "text": fmt_tw(ref_dt), "size": "sm", "color": "#9c9a92"}
                    ]
                }
            ]
        },
        "footer": footer()
    }

# ── 發送 ──────────────────────────────────────────────────

def send_flex(token, alt_text, bubble):
    payload = json.dumps({
        "messages": [{"type": "flex", "altText": alt_text, "contents": bubble}]
    }).encode('utf-8')
    req = Request(
        LINE_API_URL, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method='POST'
    )
    try:
        with urlopen(req, timeout=15) as r:
            print(f"[INFO] 通知發送成功，狀態碼: {r.status}")
            return True
    except URLError as e:
        print(f"[ERROR] 通知發送失敗: {e}", file=sys.stderr)
        return False

# ── 主程式 ────────────────────────────────────────────────

def main():
    token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
    if not token:
        print("[ERROR] 找不到 LINE_CHANNEL_ACCESS_TOKEN", file=sys.stderr)
        sys.exit(1)

    races = fetch_races()
    if not races:
        sys.exit(1)

    now_tw   = datetime.now(TW_TZ)
    today    = now_tw.date()
    week_end = today + timedelta(days=6)
    elta     = load_elta()
    force    = os.environ.get('FORCE_NOTIFY') == 'true'

    this_week = None
    next_race = None

    for race in races:
        q      = race.get('Qualifying')
        ref_dt = parse_dt_tw(q['date'], q['time']) if q else parse_dt_tw(race['date'], race.get('time', ''))
        if ref_dt < now_tw:
            continue
        if ref_dt.date() <= week_end:
            this_week = race
        else:
            next_race = race
        break

    if this_week:
        alt_text, bubble = build_race_bubble(this_week, elta)
    elif next_race:
        q          = next_race.get('Qualifying')
        ref_dt     = parse_dt_tw(q['date'], q['time']) if q else parse_dt_tw(next_race['date'], next_race.get('time', ''))
        days_until = (ref_dt.date() - today).days
        alt_text, bubble = build_no_race_bubble(next_race, days_until, ref_dt)
    else:
        alt_text = "🏁 抓無未來資料，自動判定賽季結束"
        bubble   = {
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#5F5E5A", "paddingAll": "16px",
                "contents": [
                    {"type": "text", "text": "🏁 2026 F1",      "color": "#ffffffb3", "size": "xs", "weight": "bold"},
                    {"type": "text", "text": "抓無未來資料",     "color": "#ffffff",   "size": "xl", "weight": "bold"},
                    {"type": "text", "text": "自動判定賽季結束", "color": "#ffffff99",  "size": "xs"}
                ]
            },
            "body": {
                "type": "box", "layout": "vertical", "paddingAll": "16px", "spacing": "sm",
                "contents": [
                    {"type": "text", "text": "2026 賽季", "size": "xs",  "color": "#9c9a92"},
                    {"type": "text", "text": "共 24 站",  "size": "lg",  "weight": "bold", "color": "#1a1a18"}
                ]
            },
            "footer": footer()
        }

    if force:
        alt_text = "【測試】" + alt_text

    print(f"[INFO] altText: {alt_text}")
    send_flex(token, alt_text, bubble)

if __name__ == '__main__':
    main()
