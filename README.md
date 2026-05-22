# F1 台灣車迷報表 2026

完全自動更新的 F1 報表，針對愛爾達體育 1-4 台（無 MAX 台）的台灣車迷。

## 功能

- **積分榜** — 車手 + 車隊，自動從 Jolpica F1 API 抓取，快取 1 小時
- **賽程表** — 全年 22 站，台灣時間自動換算（UTC+8），快取 24 小時
- **本站轉播** — 自動判斷下一站各場次時間、頻道、能不能看
- **全自動** — 不需要任何手動更新

## 部署到 GitHub Pages（5 分鐘）

1. 在 GitHub 建立一個新 repo（例如 `f1-tw`）
2. 把 `index.html` 上傳到 repo 根目錄
3. 到 repo 的 **Settings → Pages**
4. Source 選 **Deploy from a branch**
5. Branch 選 `main`，資料夾選 `/ (root)`，按 Save
6. 等約 1 分鐘，網址 `https://你的帳號.github.io/f1-tw` 就上線了

## 資料來源

| 資料 | 來源 | 更新頻率 |
|------|------|---------|
| 車手 / 車隊積分 | Jolpica F1 API | 頁面載入（快取 1 小時）|
| 賽程 / 場次時間 | Jolpica F1 API | 頁面載入（快取 24 小時）|
| 台灣時間換算 | UTC+8 自動計算 | 即時 |
| ELTA 頻道 | 規則判斷（Q/Race/Sprint = 體育1台，FP = MAX台）| 靜態規則 |

## 注意事項

- Jolpica API 是免費的，不需要 API key
- 快取存在 localStorage，關瀏覽器後保留
- 按「重新整理」強制清除快取重抓
- 如果 Jolpica API 有時間差，賽後幾小時才會更新積分
