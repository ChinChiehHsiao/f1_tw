#!/usr/bin/env python3
"""
從愛爾達 CDN JSON 抓取 F1 轉播頻道資訊，輸出 elta.json
API: https://piceltaott-elta.cdn.hinet.net/production/json/program_list/sports_live_program_list.json
"""

import json, sys, gzip, ssl
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

API_URL = (
    "https://piceltaott-elta.cdn.hinet.net"
    "/production/json/program_list/sports_live_program_list.json"
)
OUTPUT = "elta.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Referer": "https://eltaott.tv/channel/sports_program_detail",
    "Origin": "https://eltaott.tv",
}

# channel_number → 實際顯示台名（從 eltaott.tv 實測確認）
CHANNEL_NAME_MAP = {
    101: "愛爾達體育1台",
    105: "愛爾達體育2台",
    110: "愛爾達體育3台",
    115: "愛爾達體育4台",
    540: "愛爾達體育MAX1台",
    541: "愛爾達體育MAX2台",
    542: "愛爾達體育MAX3台",
    543: "愛爾達體育MAX4台",
    544: "愛爾達體育MAX5台",
    545: "愛爾達體育MAX6台",
    546: "愛爾達體育MAX7台",
    547: "愛爾達體育MAX8台",
    548: "愛爾達體育MAX9台",
    549: "愛爾達體育MAX10台",
}

def channel_name(num):
    return CHANNEL_NAME_MAP.get(num, f"ch{num}")

def is_max(num):
    return num >= 540

def is_original_audio(desc):
    return "原音" in desc

def is_kids(desc):
    return "Kids" in desc or "兒童" in desc

# program_desc 關鍵字 → session key（順序重要，衝刺排位賽要在衝刺賽前）
SESSION_KEYWORDS = [
    ("衝刺排位賽", "SprintQualifying"),
    ("衝刺賽",     "Sprint"),
    ("排位賽",     "Qualifying"),
    ("正賽",       "Race"),
    ("第1節自由練習", "FirstPractice"),
    ("第2節自由練習", "SecondPractice"),
    ("第3節自由練習", "ThirdPractice"),
    ("自由練習",   "FirstPractice"),  # 未標節次時預設第1節
]

def detect_session(desc):
    for kw, key in SESSION_KEYWORDS:
        if kw in desc:
            return key
    return None

def read_json_response(response):
    raw = response.read()
    enc = response.headers.get("Content-Encoding", "")
    data = gzip.decompress(raw) if "gzip" in enc else raw
    return json.loads(data.decode("utf-8"))

def fetch_json():
    req = Request(API_URL, headers=HEADERS)
    try:
        with urlopen(req, timeout=20) as r:
            return read_json_response(r)
    except URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            print("[WARN] CDN 憑證驗證失敗，改用固定來源的寬鬆 SSL 模式重試", file=sys.stderr)
            try:
                ctx = ssl._create_unverified_context()
                with urlopen(req, timeout=20, context=ctx) as r:
                    return read_json_response(r)
            except (URLError, json.JSONDecodeError) as retry_error:
                print(f"[ERROR] 重試失敗: {retry_error}", file=sys.stderr)
                return None
        print(f"[ERROR] 連線失敗: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失敗: {e}", file=sys.stderr)
        return None

def parse_f1_channels(data):
    """
    過濾條件：
    - game_type == "F1"
    - 含 LIVE，不含 D-LIVE
    同一 session 有多個頻道時，優先選非 MAX 台、非原音、非 Kids，再選最早開播
    """
    calendar = data.get("calendar", {})
    candidates = {}

    for date_str, programs in calendar.items():
        for p in programs:
            if p.get("game_type") != "F1":
                continue
            desc = p.get("program_desc", "")
            if "LIVE" not in desc or "D-LIVE" in desc:
                continue

            session = detect_session(desc)
            if not session:
                continue

            ch_num = p.get("channel_number", 0)
            entry = {
                "channel_number": ch_num,
                "channel_name":   channel_name(ch_num),
                "is_max":         is_max(ch_num),
                "desc":           desc,
                "start_time":     p.get("start_time", 0),
                "is_original":    is_original_audio(desc),
                "is_kids":        is_kids(desc),
            }
            candidates.setdefault(session, []).append(entry)
            print(f"  候選 {session:20s}  ch{ch_num:3d}  {desc[:55]}")

    # 每個 session 選最佳：
    # 1. 優先選未來的場次（start_time > now）
    # 2. 若全部都已過去，選最近的過去場次
    # 3. 非 MAX 台優先
    # 4. 非原音、非 Kids 優先
    # 5. 最早開播、頻道號碼最小優先
    now_ts = int(datetime.now(timezone.utc).timestamp())
    sessions = {}
    for session, entries in candidates.items():
        future = [e for e in entries if e["start_time"] >= now_ts]
        pool = future if future else entries
        best = sorted(pool, key=lambda e: (
            e["is_max"],
            e["is_original"],
            e["is_kids"],
            e["start_time"],
            e["channel_number"],
        ))[0]
        sessions[session] = best
        print(f"  選定 {session:20s} → {best['channel_name']}  ({best['desc'][:40]})")

    return sessions

def main():
    print(f"[INFO] 抓取 {API_URL}")
    data = fetch_json()

    if not data:
        print("[ERROR] 無法取得資料，結束", file=sys.stderr)
        sys.exit(1)

    print("[INFO] 解析 F1 場次...")
    sessions = parse_f1_channels(data)

    if not sessions:
        print("[ERROR] 找不到任何 F1 場次", file=sys.stderr)
        sys.exit(1)

    channels = {k: v["channel_name"] for k, v in sessions.items()}
    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source":  API_URL,
        "scraped": True,
        "channels": channels,
        "sessions": sessions,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 寫入 {OUTPUT} 完成")
    for k, v in sessions.items():
        print(f"  {k:20s} → {v['channel_name']}")

if __name__ == "__main__":
    main()
