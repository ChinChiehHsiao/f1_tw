# F1 台灣車迷報表 2026

🌐 **網址：https://chinchiehhsiao.github.io/f1_tw**

完全自動更新的 F1 報表，針對愛爾達體育 1-4 台（無 MAX 台）的台灣車迷。

## 功能

- **積分榜** — 車手 + 車隊，自動從 Jolpica F1 API 抓取，快取 1 小時
- **賽程表** — 全年 22 站，台灣時間自動換算（UTC+8），快取 24 小時
- **本站轉播** — 自動判斷下一站各場次時間、頻道、能不能看
- **全自動** — 不需要任何手動更新

## 自動化原理

這個報表完全不需要後端伺服器或手動維護，靠以下機制自動運作：

### 積分榜 & 賽程
每次開啟網頁時，瀏覽器直接呼叫 [Jolpica F1 API](https://api.jolpi.ca/ergast/f1/)（免費、無需 API key）：
- `GET /ergast/f1/2026/driverStandings.json` — 車手積分
- `GET /ergast/f1/2026/constructorStandings.json` — 車隊積分
- `GET /ergast/f1/2026.json` — 全年賽程與各場次 UTC 時間

Jolpica 在每場賽事結束後約 1-2 小時自動更新，不需要任何人工操作。

### 台灣時間換算
API 回傳的時間都是 UTC，網頁前端直接加 8 小時換算成台灣時間（UTC+8），不依賴任何外部服務。

### 轉播頻道判斷
根據愛爾達 2026-2029 賽季官方公告的固定規則自動判斷：
- **體育 1 台**：正賽、排位賽、衝刺賽、衝刺排位賽
- **MAX 台**：自由練習 FP1/FP2/FP3、F2、F3 等

不需要爬蟲，頻道規則整季固定，寫死在前端邏輯裡。

### 快取機制
為了減少 API 請求，資料存在瀏覽器的 localStorage：
- 積分：快取 1 小時（賽事日改為 15 分鐘）
- 賽程：快取 24 小時
- 按「重新整理」按鈕可強制清除快取重抓

### 部署
GitHub Pages 直接 host 靜態 HTML，push 後自動部署，完全免費，沒有伺服器成本。

## 部署到 GitHub Pages（5 分鐘）

1. 在 GitHub 建立一個新 repo（例如 `f1_tw`）
2. 把 `index.html` 上傳到 repo 根目錄
3. 到 repo 的 **Settings → Pages**
4. Source 選 **Deploy from a branch**
5. Branch 選 `main`，資料夾選 `/ (root)`，按 Save
6. 等約 1 分鐘，網址 `https://你的帳號.github.io/f1_tw` 就上線了

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
