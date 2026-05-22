#!/usr/bin/env python3
"""
爬取 HamiVideo F1 賽程表，輸出 elta.json
GitHub Actions 自動執行
"""

import re, json, sys, gzip
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import URLError

URL = "https://hamivideo.hinet.net/main/317.do"
OUTPUT = "elta.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

# 節目名稱 → API session key
SESSION_MAP = {
    "正賽":       "Race",
    "衝刺排位賽": "SprintQualifying",
    "衝刺資格賽": "SprintQualifying",
    "衝刺賽":     "Sprint",
    "排位賽":     "Qualifying",
    "自由練習一": "FirstPractice",
    "自由練習二": "SecondPractice",
    "自由練習三": "ThirdPractice",
    "FP1":        "FirstPractice",
    "FP2":        "SecondPractice",
    "FP3":        "ThirdPractice",
}

DEFAULT_CHANNELS = {
    "Race":             "體育1-4台",
    "Qualifying":       "體育1-4台",
    "Sprint":           "體育1-4台",
    "SprintQualifying": "體育1-4台",
    "FirstPractice":    "MAX台",
    "SecondPractice":   "MAX台",
    "ThirdPractice":    "MAX台",
}


def fetch_html():
    req = Request(URL, headers=HEADERS)
    try:
        with urlopen(req, timeout=20) as r:
            raw = r.read()
            enc = r.headers.get("Content-Encoding", "")
            return gzip.decompress(raw).decode("utf-8", errors="replace") if "gzip" in enc else raw.decode("utf-8", errors="replace")
    except URLError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        return None


def detect_session(name):
    for kw, key in SESSION_MAP.items():
        if kw in name:
            return key
    return None


def parse_schedule(html):
    # 清除 script/style，把標籤轉換為換行
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.I)
    text = re.sub(r"<style[^>]*>.*?</style>",  "", text, flags=re.DOTALL | re.I)
    text = re.sub(r"<[^>]+>", "\n", text)
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    channels = {}
    ch_re = re.compile(r"愛爾達體育(MAX)?(\d+)台")

    for i, line in enumerate(lines):
        # 只看 LIVE F1 場次，跳過延播（D-LIVE）
        if not re.search(r"^LIVE\s+F1\s+", line):
            continue

        stype = detect_session(line)
        if not stype or stype in channels:
            continue

        # 往前 8 行找頻道名稱
        for j in range(max(0, i - 8), i):
            m = ch_re.search(lines[j])
            if m:
                is_max = bool(m.group(1))
                num = m.group(2)
                ch = f"愛爾達體育MAX{num}台" if is_max else f"愛爾達體育{num}台"
                channels[stype] = ch
                print(f"  {stype:20s} → {ch}  ({line[:55]})")
                break

    return channels


def main():
    print(f"[INFO] 抓取 {URL}")
    html = fetch_html()

    if not html:
        print("[WARN] 抓取失敗，使用預設規則", file=sys.stderr)
        scraped = False
        channels = DEFAULT_CHANNELS.copy()
    else:
        print("[INFO] 解析中...")
        channels = parse_schedule(html)
        if not channels:
            print("[WARN] 無 F1 場次資料，使用預設規則", file=sys.stderr)
            scraped = False
            channels = DEFAULT_CHANNELS.copy()
        else:
            scraped = True
            for k, v in DEFAULT_CHANNELS.items():
                channels.setdefault(k, v)

    result = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": URL,
        "scraped": scraped,
        "channels": channels,
    }

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[INFO] 寫入 {OUTPUT} 完成")
    for k, v in channels.items():
        print(f"  {k:20s} → {v}")


if __name__ == "__main__":
    main()
