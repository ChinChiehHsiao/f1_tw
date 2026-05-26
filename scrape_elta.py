#!/usr/bin/env python3
"""
從愛爾達 CDN JSON 抓取 F1 轉播頻道資訊，輸出 elta.json
1. 先從 Jolpica API 取得下一站賽程，判斷是否有衝刺賽
2. 再從愛爾達 API 抓對應場次的頻道資訊
"""

import json, sys, gzip, re
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

ELTA_URL = (
    "https://piceltaott-elta.cdn.hinet.net"
    "/production/json/program_list/sports_live_program_list.json"
)
JOLPICA_URL = "https://api.jolpi.ca/ergast/f1/2026.json"
OUTPUT = "elta.json"

ELTA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Referer": "https://eltaott.tv/channel/sports_program_detail",
    "Origin": "https://eltaott.tv",
}

JOLPICA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# ---- 工具函式 ----

def fetch(url, headers):
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=20) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            data = gzip.decompress(raw) if "gzip" in enc else raw
            return json.loads(data.decode("utf-8"))
    except URLError as e:
        print(f"[ERROR] 連線失敗 {url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失敗: {e}", file=sys.stderr)
        return None

def channel_name(num):
    if 101 <= num <= 199:
        return f"愛爾達體育{num - 100}台"
    if 540 <= num <= 599:
        return f"愛爾達體育MAX{num - 539}台"
    return f"ch{num}"

def is_max(num):
    return num >= 540

def extract_race_name(desc):
    """從 program_desc 抽出賽站名稱，例如『摩納哥站』"""
    m = re.match(r'^(.+?站)', desc)
    return m.group(1) if m else None

# session 判斷關鍵字（順序重要）
SESSION_KEYWORDS = [
    ("衝刺排位賽",    "SprintQualifying"),
    ("衝刺賽",        "Sprint"),
    ("排位賽",        "Qualifying"),
    ("正賽",          "Race"),
    ("第1節自由練習", "FirstPractice"),
    ("第2節自由練習", "SecondPractice"),
    ("第3節自由練習", "ThirdPractice"),
    ("自由練習",      "FirstPractice"),
]

def detect_session(desc):
    for kw, key in SESSION_KEYWORDS:
        if kw in desc:
            return key
    return None

# ---- 步驟1：從 Jolpica 取得下一站資訊 ----

def get_next_race_info():
    """
    回傳 dict:
      race_name: str（中文）
      has_sprint: bool
      race_utc: int（正賽 Unix timestamp）
    """
    print(f"[INFO] 查詢 Jolpica 賽程...")
    data = fetch(JOLPICA_URL, JOLPICA_HEADERS)
    if not data:
        return None

    races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    now_ts = int(datetime.now(timezone.utc).timestamp())

    # 找下一場未來的正賽
    for race in races:
        race_date = race.get("date", "")
        race_time = race.get("time", "00:00:00Z")
        race_ts = int(datetime.fromisoformat(
            f"{race_date}T{race_time}".replace("Z", "+00:00")
        ).timestamp())
        if race_ts > now_ts:
            has_sprint = "Sprint" in race or "SprintQualifying" in race
            race_name = race.get("raceName", "")
            print(f"[INFO] 下一站：{race_name}，有衝刺賽：{has_sprint}")
            return {
                "race_name_en": race_name,
                "has_sprint":   has_sprint,
                "race_utc":     race_ts,
            }

    print("[WARN] 找不到未來賽程", file=sys.stderr)
    return None

# ---- 步驟2：從愛爾達 API 抓頻道 ----

# 英文賽站名 → 中文（用於比對愛爾達節目表）
RACE_NAME_MAP = {
    "Australian Grand Prix":    "澳洲站",
    "Chinese Grand Prix":       "中國站",
    "Japanese Grand Prix":      "日本站",
    "Bahrain Grand Prix":       "巴林站",
    "Saudi Arabian Grand Prix": "沙烏地站",
    "Miami Grand Prix":         "邁阿密站",
    "Canadian Grand Prix":      "加拿大站",
    "Monaco Grand Prix":        "摩納哥站",
    "Spanish Grand Prix":       "西班牙站",
    "Austrian Grand Prix":      "奧地利站",
    "British Grand Prix":       "英國站",
    "Belgian Grand Prix":       "比利時站",
    "Hungarian Grand Prix":     "匈牙利站",
    "Dutch Grand Prix":         "荷蘭站",
    "Italian Grand Prix":       "義大利站",
    "Azerbaijan Grand Prix":    "亞塞拜然站",
    "Singapore Grand Prix":     "新加坡站",
    "United States Grand Prix": "美國站",
    "Mexico City Grand Prix":   "墨西哥站",
    "São Paulo Grand Prix":     "巴西站",
    "Las Vegas Grand Prix":     "拉斯維加斯站",
    "Qatar Grand Prix":         "卡達站",
    "Abu Dhabi Grand Prix":     "阿布達比站",
    "Madrid Grand Prix":        "馬德里站",
}

def best_entry(entries):
    """
    選最佳頻道：
    1. 非MAX台優先
    2. start_time 最早（最近的場次）
    3. channel_number 最小
    """
    non_max = [e for e in entries if not e["is_max"]]
    pool = non_max if non_max else entries
    return sorted(pool, key=lambda e: (e["start_time"], e["channel_number"]))[0]

def parse_elta(elta_data, race_name_tw, has_sprint):
    """
    從愛爾達資料找出指定賽站的頻道資訊。
    - 不論 MAX 或一般台都收，最後再選最佳
    - FP：有一般台就標可看，只有 MAX 就標不可看
    - Qualifying/Race：同上
    - Sprint/SQ：只在 has_sprint 為 True 時才抓
    """
    calendar = elta_data.get("calendar", {})
    candidates = {}  # session -> list of entries

    for date_str, programs in calendar.items():
        for p in programs:
            if p.get("game_type") != "F1":
                continue
            desc = p.get("program_desc", "")
            if "LIVE" not in desc or "D-LIVE" in desc:
                continue
            if "車手遊行" in desc or "Kids" in desc:
                continue

            # 確認是同一賽站
            if race_name_tw not in desc:
                continue

            session = detect_session(desc)
            if not session:
                continue

            # 衝刺賽只在有衝刺週時才抓
            if session in ("SprintQualifying", "Sprint") and not has_sprint:
                continue

            ch_num = p.get("channel_number", 0)
            entry = {
                "channel_number": ch_num,
                "channel_name":   channel_name(ch_num),
                "is_max":         is_max(ch_num),
                "desc":           desc,
                "start_time":     p.get("start_time", 0),
            }
            candidates.setdefault(session, []).append(entry)
            print(f"  候選 {session:20s}  ch{ch_num:3d}  {desc[:55]}")

    # 選定每個 session 的最佳頻道
    channels = {}
    for session, entries in candidates.items():
        best = best_entry(entries)
        channels[session] = best["channel_name"]
        print(f"  選定 {session:20s} → {best['channel_name']}  ({best['desc'][:45]})")

    return channels

# ---- 主程式 ----

def main():
    # 1. 取得下一站資訊
    next_race = get_next_race_info()
    if not next_race:
        print("[ERROR] 無法取得賽程資訊", file=sys.stderr)
        sys.exit(1)

    race_name_tw = RACE_NAME_MAP.get(next_race["race_name_en"])
    if not race_name_tw:
        print(f"[ERROR] 找不到對應中文站名：{next_race['race_name_en']}", file=sys.stderr)
        sys.exit(1)

    has_sprint = next_race["has_sprint"]
    print(f"[INFO] 目標賽站：{race_name_tw}，衝刺週：{has_sprint}")

    # 2. 抓愛爾達資料
    print(f"[INFO] 抓取愛爾達節目表...")
    elta_data = fetch(ELTA_URL, ELTA_HEADERS)
    if not elta_data:
        print("[ERROR] 無法取得愛爾達資料", file=sys.stderr)
        sys.exit(1)

    # 3. 解析頻道
    print(f"[INFO] 解析 {race_name_tw} 場次...")
    channels = parse_elta(elta_data, race_name_tw, has_sprint)

    if not channels:
        print(f"[ERROR] 找不到 {race_name_tw} 的任何場次", file=sys.stderr)
        sys.exit(1)

    # 4. 寫入 elta.json
    result = {
        "updated":   datetime.now(timezone.utc).isoformat(),
        "source":    ELTA_URL,
        "scraped":   True,
        "race_name": race_name_tw,
        "channels":  channels,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 寫入 {OUTPUT} 完成")
    for k, v in channels.items():
        print(f"  {k:20s} → {v}")

if __name__ == "__main__":
    main()
