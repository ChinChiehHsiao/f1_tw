#!/usr/bin/env python3
"""
從愛爾達 CDN JSON 抓取 F1 轉播頻道資訊，輸出 elta.json
API: https://piceltaott-elta.cdn.hinet.net/production/json/program_list/sports_live_program_list.json
"""

import json, sys, gzip
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

# 頻道號碼 → 頻道名稱
CHANNEL_MAP = {
    101: "愛爾達體育1台",
    102: "愛爾達體育2台",
    103: "愛爾達體育3台",
    104: "愛爾達體育4台",
    105: "愛爾達體育5台",
}
MAX_CHANNEL_RANGE = range(540, 560)  # 540-559 都是 MAX 台

# program_desc 關鍵字 → session key
SESSION_KEYWORDS = [
    ("衝刺排位賽", "SprintQualifying"),
    ("衝刺賽",     "Sprint"),
    ("排位賽",     "Qualifying"),
    ("自由練習",   "FP"),   # 先抓到再細分節次
    ("正賽",       "Race"),
]

# 自由練習節次
FP_MAP = {
    "第1節": "FirstPractice",
    "第2節": "SecondPractice",
    "第3節": "ThirdPractice",
}


def channel_name(num):
    if num in CHANNEL_MAP:
        return CHANNEL_MAP[num]
    if num in MAX_CHANNEL_RANGE:
        return f"愛爾達體育MAX台(ch{num})"
    return f"ch{num}"


def is_max(num):
    return num in MAX_CHANNEL_RANGE


def detect_session(desc):
    """從 program_desc 判斷 session key"""
    for kw, key in SESSION_KEYWORDS:
        if kw in desc:
            if key == "FP":
                for fp_kw, fp_key in FP_MAP.items():
                    if fp_kw in desc:
                        return fp_key
                return "FirstPractice"  # 預設第1節
            return key
    return None


def fetch_json():
    req = Request(API_URL, headers=HEADERS)
    try:
        with urlopen(req, timeout=20) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            data = gzip.decompress(raw) if "gzip" in enc else raw
            return json.loads(data.decode("utf-8"))
    except URLError as e:
        print(f"[ERROR] 連線失敗: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 解析失敗: {e}", file=sys.stderr)
        return None


def parse_f1_channels(data):
    """
    遍歷 calendar 裡所有日期，找出 F1 LIVE 場次。
    只取中文主播版（排除含「英文解說」或「原音」的場次）。
    同一個 session key 若有多個場次（不同頻道），優先取非 MAX 台。
    """
    calendar = data.get("calendar", {})
    candidates = {}  # session_key -> list of {channel_number, channel_name, desc, start_time}

    for date_str, programs in calendar.items():
        for p in programs:
            if p.get("game_type") != "F1":
                continue
            desc = p.get("program_desc", "")
            if "LIVE" not in desc or "D-LIVE" in desc:
                continue
            # 跳過英文原音版
            if "英文解說" in desc or "原音" in desc:
                continue

            session = detect_session(desc)
            if not session:
                continue

            ch_num = p.get("channel_number", 0)
            entry = {
                "channel_number": ch_num,
                "channel_name": channel_name(ch_num),
                "is_max": is_max(ch_num),
                "desc": desc,
                "start_time": p.get("start_time", 0),
            }

            if session not in candidates:
                candidates[session] = []
            candidates[session].append(entry)
            print(f"  找到 {session:20s} ch{ch_num:3d} {desc[:50]}")

    # 每個 session 選最佳頻道：優先非 MAX、再依 start_time 最早
    channels = {}
    for session, entries in candidates.items():
        non_max = [e for e in entries if not e["is_max"]]
        pool = non_max if non_max else entries
        best = sorted(pool, key=lambda e: e["start_time"])[0]
        channels[session] = best["channel_name"]
        print(f"  選定 {session:20s} → {best['channel_name']} ({best['desc'][:40]})")

    return channels


def main():
    print(f"[INFO] 抓取 {API_URL}")
    data = fetch_json()

    if not data:
        print("[ERROR] 無法取得資料，結束", file=sys.stderr)
        sys.exit(1)

    print("[INFO] 解析 F1 場次...")
    channels = parse_f1_channels(data)

    if not channels:
        print("[ERROR] 找不到任何 F1 場次", file=sys.stderr)
        sys.exit(1)

    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": API_URL,
        "scraped": True,
        "channels": channels,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n[INFO] 寫入 {OUTPUT}")
    for k, v in channels.items():
        print(f"  {k:20s} → {v}")


if __name__ == "__main__":
    main()
