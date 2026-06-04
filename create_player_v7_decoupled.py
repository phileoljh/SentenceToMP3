import os
import json
import re
import urllib.parse

# =================設定區=================
MP3_DIR = "MP3_Output"                 # MP3 音檔儲存資料夾
INPUT_FILE = "mp3.md"                  # 來源 Markdown 單字檔案
JS_PLAYLIST_FILE = "playlist.js"       # 產出的解耦資料檔名
HTML_FILE = "player.html"              # 產出的全域單一播放器網頁檔名
READ_HTML_FILE = "mp3.html"            # 產出的全域閱讀清單網頁檔名
# ========================================

def parse_md_file(filepath):
    """
    解析 Markdown 表格格式的 mp3.md 檔案
    支援 4 欄或 5 欄表格結構
    格式範例: | (序號) English | 中文 | 例句 | 例句中譯 |
    """
    word_data = []
    
    if not os.path.exists(filepath):
        print(f"⚠️ 警告：找不到 {filepath}，網頁將只顯示音檔名稱。")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line_strip = line.strip()
            
            # 僅處理表格行
            if not line_strip.startswith("|"):
                continue
            
            # 排除分隔線
            if "---" in line_strip:
                continue

            # 使用管線符號分割欄位
            parts = [p.strip() for p in line_strip.split('|')]
            # 去除 split 產生的頭尾空元素 (若表格開頭結尾都有 |)
            if parts[0] == "": 
                parts.pop(0)
            if parts and parts[-1] == "": 
                parts.pop()

            # 偵測並相容 4 欄或 5 欄格式
            if len(parts) >= 5:
                # 5 欄位格式: | 序號 | 英文 | 中文 | 例句 | 中文例句 |
                raw_word = parts[1]
                meaning = parts[2]
                sentence = parts[3]
                sentence_trans = parts[4]
            elif len(parts) >= 2:
                # 4 欄位格式: | (序號) 英文 | 中文 | 例句 | 中譯 |
                raw_word = parts[0]
                meaning = parts[1]
                sentence = parts[2] if len(parts) >= 3 else ""
                sentence_trans = parts[3] if len(parts) >= 4 else ""
            else:
                continue

            # 清理單字開頭的數字序號 (如 "1. apple" 轉為 "apple")
            clean_word = re.sub(r'^\d+\.\s*', '', raw_word)
            if not clean_word:
                continue

            # 精確比對表頭欄位內容，避免誤殺一般行 (如 be proficient in)
            header_vals = ["(序號) English", "English", "序號", "英文片語", "英文", "word", "序號 English"]
            if clean_word in header_vals:
                continue

            word_data.append({
                "word": clean_word,
                "meaning": meaning,
                "sentence": sentence,
                "sentence_trans": sentence_trans
            })
    return word_data

def generate_player():
    """
    主生成函式：
    1. 解析 md 檔案資料。
    2. 直接以單字表順序產生播放清單與檔名。
    3. 生成 playlist.js 資料檔。
    4. 生成 player_v7_decoupled.html 播放器網頁引擎。
    """
    # 解析單字清單資料 (Source of Truth)
    text_data = parse_md_file(INPUT_FILE)
    
    if not text_data:
        print("⚠️ 警告：沒有偵測到任何有效的單字資料。")
        return

    playlist = []
    
    # 建立播放清單結構
    for i, item in enumerate(text_data):
        index = i + 1
        # 清理英文單字取得合法檔名
        safe_filename_text = re.sub(r'[\\/*?:"<>|]', "", item["word"])
        filename = f"{index:04d}_{safe_filename_text}.mp3"
        
        # 進行 URL 編碼以解決特殊字元 (如空白、百分比) 在網頁載入時的 CORS 或解析失敗問題
        encoded_filename = urllib.parse.quote(filename)
        
        playlist_item = {
            "file": f"{MP3_DIR}/{encoded_filename}",
            "word": item["word"],
            "meaning": item["meaning"],
            "sentence": item["sentence"],
            "sentence_trans": item["sentence_trans"]
        }
        playlist.append(playlist_item)

    # 1. 寫入解耦後的 playlist.js 檔案
    # 透過 window.playlistData 宣告，讓本地端 (file://) 可以無障礙載入，避開 CORS 同源政策限制
    js_playlist_content = f"window.playlistData = {json.dumps(playlist, ensure_ascii=False, indent=2)};"
    with open(JS_PLAYLIST_FILE, "w", encoding="utf-8") as js_f:
        js_f.write(js_playlist_content)
    print(f"✅ 資料解耦完成！已生成: {JS_PLAYLIST_FILE}")

    # 2. 寫入高質感解耦播放器 player_v7_decoupled.html 檔案
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字聽力訓練(毛玻璃解耦版)</title>
    <!-- 載入 Google Fonts 設計字體與 Font Awesome 6 圖示 -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    
    <style>
        :root {{
            --bg-color: #0f172a;
            --surface-color: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary-color: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.3);
            --accent-success: #10b981;
            --accent-success-glow: rgba(16, 185, 129, 0.2);
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --card-radius: 20px;
            --btn-radius: 10px;
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            background-color: var(--bg-color);
            background-image:
                radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.15) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(236, 72, 153, 0.08) 0%, transparent 40%);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 0;
        }}

        .app-container {{
            width: 100%;
            max-width: 680px;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }}

        /* 固定頂部控制面板，採用高級毛玻璃質感 */
        .player-header {{
            position: sticky;
            top: 0;
            background: rgba(15, 23, 42, 0.75);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 20px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
            border-bottom-left-radius: var(--card-radius);
            border-bottom-right-radius: var(--card-radius);
        }}

        .header-title {{
            font-family: 'Outfit', sans-serif;
            font-size: 1.3rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 15px;
            background: linear-gradient(135deg, #fff 40%, var(--primary-color) 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.02em;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }}

        .header-title i {{
            color: var(--primary-color);
            -webkit-text-fill-color: initial;
        }}

        /* 目前播放單字卡片 */
        #current-info {{
            text-align: center;
            margin-bottom: 15px;
            min-height: 140px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 15px;
            box-shadow: inset 0 0 12px rgba(255, 255, 255, 0.03);
            transition: var(--transition);
        }}

        #current-word {{
            /* 將字型由 Outfit 改為 Inter 並調降字體粗細至 700 (Bold)，優化小寫 t 的可讀性 (帶有向右彎曲尾巴) 避免其形似十字架 */
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            font-size: 1.8rem;
            font-weight: 700;
            color: #fff;
            margin-bottom: 6px;
            letter-spacing: -0.01em;
            transition: var(--transition);
        }}

        #current-meaning {{
            font-size: 1.05rem;
            color: var(--primary-color);
            font-weight: 600;
            margin-bottom: 8px;
        }}
        
        .sentence-box {{
            margin-top: 5px;
            padding-top: 8px;
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        
        #current-sentence {{
            font-size: 0.9rem;
            color: var(--text-dim);
            font-style: italic;
            line-height: 1.4;
        }}
        
        #current-sentence-trans {{
            font-size: 0.85rem;
            color: rgba(148, 163, 184, 0.7);
        }}
        
        /* 播放器按鈕樣式 */
        audio {{
            width: 100%;
            margin-bottom: 12px;
            height: 40px;
            border-radius: 30px;
            opacity: 0.9;
        }}

        /* 左右中三欄單一橫列整合控制面板：極致節省垂直空間 */
        .controls-panel {{
            position: relative; /* 為中間絕對居中提供定位基準 */
            display: flex;
            justify-content: space-between;
            align-items: center; /* 讓左、中、右三側完美垂直置中對齊 */
            gap: 10px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid rgba(255, 255, 255, 0.03);
            padding: 8px 12px; /* 緊湊的上下 padding */
            border-radius: 14px;
            min-height: 54px; /* 固定最小高度，確保絕對定位時高度不塌陷 */
        }}

        /* 左側設定區：間隔與重複一上一下堆疊 */
        .left-settings {{
            display: flex;
            flex-direction: column;
            gap: 4px; /* 緊湊的垂直間距 */
            flex-shrink: 0;
            z-index: 1; /* 保證層級正確 */
        }}

        .control-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            color: var(--text-dim);
        }}

        .control-item label {{
            white-space: nowrap;
            width: 48px; /* 擴寬至 48px，提供舒適間隔防止文字頂到數字 */
            display: inline-block;
        }}

        .control-item input {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 4px 8px; /* 稍微增加 padding */
            border-radius: 6px;
            width: 100%;
            max-width: 80px; /* 大幅加寬至 80px，預留三位數與上下按鈕並存空間 */
            font-size: 0.85rem;
            outline: none;
            transition: var(--transition);
        }}

        .control-item input:focus {{
            border-color: var(--primary-color);
            box-shadow: 0 0 6px var(--primary-glow);
        }}

        /* 中間播控按鈕區 - 絕對居中法，保證 100% 精準位於播放器中軸 */
        .center-controls {{
            position: absolute;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            flex-shrink: 0;
            z-index: 2; /* 確保點擊層級最高 */
        }}

        /* 縮小版上一首/下一首圓形按鈕 */
        button.player-btn.small-btn {{
            width: 36px;
            height: 36px;
            border: 1px solid var(--border-color);
            background: rgba(255, 255, 255, 0.03);
            border-radius: 50%;
            cursor: pointer;
            font-size: 0.9rem;
            color: var(--text-main);
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
        }}

        button.player-btn.small-btn:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--text-dim);
            transform: scale(1.05);
        }}

        /* 縮小版播放/暫停按鈕 */
        #playPauseBtn.main-play-btn {{
            min-width: 130px;
            padding: 0 16px;
            white-space: nowrap;
            height: 36px;
            border-radius: var(--btn-radius);
            background: var(--primary-color);
            font-weight: 700;
            font-size: 0.85rem;
            color: white;
            border: none;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            box-shadow: 0 4px 12px var(--primary-glow);
            transition: var(--transition);
        }}

        #playPauseBtn.main-play-btn:hover {{
            background: #4f46e5;
            box-shadow: 0 6px 16px rgba(99, 102, 241, 0.45);
        }}

        /* 右側設定區：跳轉區 */
        .right-settings {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 0.8rem;
            color: var(--text-dim);
            flex-shrink: 0;
            z-index: 1; /* 保持層級正確 */
        }}

        .right-settings label {{
            white-space: nowrap;
        }}

        .right-settings input {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 5px 8px;
            border-radius: 6px;
            outline: none;
            transition: var(--transition);
        }}

        .right-settings input:focus {{
            border-color: var(--primary-color);
            box-shadow: 0 0 6px var(--primary-glow);
        }}

        .jump-btn {{
            padding: 5px 10px;
            background: var(--primary-color);
            border: none;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 600;
            white-space: nowrap;
            transition: var(--transition);
        }}

        .jump-btn:hover {{
            background: #4f46e5;
        }}

        /* 即時搜尋框樣式 */
        .search-container {{
            margin: 15px 0 0 0;
            position: relative;
        }}

        .search-container i {{
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-dim);
            font-size: 0.9rem;
        }}

        #searchInput {{
            width: 100%;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 10px 12px 10px 36px;
            border-radius: 12px;
            font-size: 0.9rem;
            outline: none;
            transition: var(--transition);
        }}

        #searchInput:focus {{
            border-color: var(--primary-color);
            box-shadow: 0 0 10px var(--primary-glow);
            background: rgba(15, 23, 42, 0.7);
        }}

        /* 下方播放清單容器 */
        .playlist-container {{
            padding: 20px;
            flex-grow: 1;
            padding-bottom: 200px;
            width: 100%;
        }}

        .playlist {{
            list-style: none;
            padding: 0;
            margin: 0;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }}

        .playlist li {{
            padding: 12px 15px;
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            transition: var(--transition);
        }}

        .playlist li:hover {{
            transform: translateY(-2px);
            border-color: rgba(99, 102, 241, 0.25);
            background: rgba(30, 41, 59, 0.9);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .playlist li.active {{
            background: rgba(99, 102, 241, 0.15);
            border-color: var(--primary-color);
            box-shadow: 0 0 15px rgba(99, 102, 241, 0.1);
        }}

        .track-num {{
            font-family: 'Outfit', sans-serif;
            font-size: 0.85rem;
            color: var(--text-dim);
            width: 32px;
            text-align: center;
            font-weight: 600;
            flex-shrink: 0;
        }}

        .track-content {{
            flex-grow: 1;
            margin-left: 10px;
            overflow: hidden;
        }}

        .track-word {{
            font-weight: 700;
            font-size: 1rem;
            color: #fff;
            display: block;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .track-meaning {{
            font-size: 0.85rem;
            color: var(--text-dim);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: block;
            margin-top: 2px;
        }}

        .playlist li.active .track-word {{
            color: var(--primary-color);
        }}

        /* 休息中倒數狀態效果 */
        .resting-state #current-info {{
            border-color: var(--accent-success);
            box-shadow: 0 0 15px var(--accent-success-glow);
        }}

        .resting-state #current-word {{
            color: var(--accent-success);
        }}

        /* 找不到搜尋結果之空狀態 */
        .empty-search {{
            text-align: center;
            padding: 40px 20px;
            color: var(--text-dim);
            font-size: 0.95rem;
        }}

        .empty-search i {{
            font-size: 2rem;
            margin-bottom: 12px;
            color: rgba(255,255,255,0.15);
            display: block;
        }}
    </style>
</head>
<body>

    <div class="app-container" id="appBody">
        <div class="player-header">
            <h2 class="header-title"><i class="fa-solid fa-graduation-cap"></i> 聽力大師(解耦版)</h2>
            
            <!-- 目前朗讀單字顯示區 -->
            <div id="current-info">
                <span id="current-word">讀取清單中...</span>
                <span id="current-meaning"></span>
                
                <div class="sentence-box">
                    <span id="current-sentence"></span>
                    <span id="current-sentence-trans"></span>
                </div>
            </div>

            <!-- HTML5 音源器 -->
            <audio id="audioPlayer" controls></audio>
            
            <!-- 
              【繁體中文註解 - 單列儀表板極致空間壓縮說明】
              此處將「播控按鈕」與「參數設定」融合為單一橫列 Flex 儀表板，節省 60% 垂直空間：
              - 左側 (left-settings)：間隔與重複一上一下堆疊，寬度經 80px 拓寬優化。
              - 中間 (center-controls)：上一首、播放/暫停、下一首水平排列，使用緊湊按鈕尺寸。
              - 右側 (right-settings)：跳至與跳轉水平排列，輸入框最大寬度統一為 80px。
              三者於同一 Flex 基準線上垂直居中對齊，完美兼顧操作熱區與介面精美度。請勿隨意拆分。
            -->
            <!-- 整合式控制儀表板 -->
            <div class="controls-panel">
                <!-- 左側：間隔與重複一上一下堆疊 -->
                <div class="left-settings">
                    <div class="control-item">
                        <label><i class="fa-solid fa-hourglass-half"></i> 間隔</label>
                        <!-- 
                          【繁體中文註解 - 寬度設計說明】
                          此處 max-width 設為 80px，用以預留「三位數（如 10.5）」與「瀏覽器原生上下微調按鈕」並存空間，
                          防止微調按鈕浮現時遮擋數字，請勿改窄。
                        -->
                        <input type="number" id="delayInput" value="1.0" min="0" step="0.5" style="max-width: 80px;">
                    </div>
                    <div class="control-item">
                        <label><i class="fa-solid fa-rotate"></i> 重複</label>
                        <!-- 
                          【繁體中文註解 - 寬度設計說明】
                          此處 max-width 設為 80px，用以預留「三位數（如 999）」與「瀏覽器原生上下微調按鈕」並存空間，
                          防止微調按鈕浮現時遮擋數字，請勿改窄。
                        -->
                        <input type="number" id="repeatInput" value="1" min="1" step="1" style="max-width: 80px;">
                    </div>
                </div>

                <!-- 中間：播控按鈕區 (水平置中) -->
                <div class="center-controls">
                    <button class="player-btn small-btn" onclick="playPrev()" title="上一首"><i class="fa-solid fa-backward-step"></i></button>
                    <button class="player-btn main-play-btn" id="playPauseBtn" onclick="togglePlay()"><i class="fa-solid fa-play"></i> 播放</button>
                    <button class="player-btn small-btn" onclick="playNext(true)" title="下一首"><i class="fa-solid fa-forward-step"></i></button>
                </div>

                <!-- 右側：跳轉區 (水平排列) -->
                <div class="right-settings">
                    <label>跳至</label>
                    <!-- 跳轉框同步加寬至 80px，達成完全的對稱美學 -->
                    <input type="number" id="jumpInput" placeholder="編號" min="1" style="width: 100%; max-width: 80px;">
                    <button onclick="jumpToTrack()" class="jump-btn">跳轉</button>
                </div>
            </div>

            <!-- 搜尋過濾器 -->
            <div class="search-container">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" id="searchInput" placeholder="在清單中搜尋英文單字或中文釋義..." oninput="filterPlaylist()">
            </div>
        </div>

        <!-- 播放清單區 -->
        <div class="playlist-container">
            <ul class="playlist" id="playlist-ui"></ul>
        </div>
    </div>

    <!-- 移除靜態引入，改為動態載入以相容全域播放與本地 CORS 限制 -->

    <script>
        let rawPlaylist = [];
        let activePlaylist = [];
        let activeIndices = [];

        let currentIndex = 0;       // 目前播音的原始索引
        let currentPlayCount = 1;   // 目前單字播放次數計數
        let gapTimer = null;        // 間隔計時器
        let gapRemaining = 0;       // 剩餘間隔毫秒數
        let gapStartTime = 0;       // 間隔開始時間戳記
        let isGapPaused = false;    // 是否暫停間隔倒數
        let restIntervalId = null;  // 倒數視覺刷新計時器

        const appBody = document.getElementById('appBody');
        const audio = document.getElementById('audioPlayer');
        const displayWord = document.getElementById('current-word');
        const displayMeaning = document.getElementById('current-meaning');
        const displaySentence = document.getElementById('current-sentence');
        const displaySentenceTrans = document.getElementById('current-sentence-trans');
        const playlistUi = document.getElementById('playlist-ui');
        const delayInput = document.getElementById('delayInput');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const jumpInput = document.getElementById('jumpInput');
        const searchInput = document.getElementById('searchInput');

        // 1. 解析網址參數
        const urlParams = new URLSearchParams(window.location.search);
        const packName = urlParams.get('pack') || '';

        // 2. 動態加載資料檔與修正路徑
        function loadDataAndInit() {{
            if (packName) {{
                const script = document.createElement('script');
                script.src = `${{encodeURIComponent(packName)}}/playlist.js`;
                script.onerror = () => {{
                    showError(`無法載入詞彙包 "${{packName}}" 的資料，請確認資料夾與 playlist.js 是否存在。`);
                }};
                script.onload = () => {{
                    if (window.playlistData && window.playlistData.length > 0) {{
                        // 在音檔路徑前方補上子目錄路徑前綴
                        window.playlistData.forEach(item => {{
                            item.file = `${{packName}}/${{item.file}}`;
                        }});
                        rawPlaylist = window.playlistData;
                        activePlaylist = [...rawPlaylist];
                        activeIndices = rawPlaylist.map((_, i) => i);
                        initPlayer();
                    }} else {{
                        showError(`詞彙包 "${{packName}}" 內無有效單字資料。`);
                    }}
                }};
                document.head.appendChild(script);
            }} else {{
                const script = document.createElement('script');
                script.src = 'playlist.js';
                script.onerror = () => {{
                    showError("找不到根目錄的 playlist.js。請確認已執行生成腳本！");
                }};
                script.onload = () => {{
                    if (window.playlistData && window.playlistData.length > 0) {{
                        rawPlaylist = window.playlistData;
                        activePlaylist = [...rawPlaylist];
                        activeIndices = rawPlaylist.map((_, i) => i);
                        initPlayer();
                    }} else {{
                        showError("根目錄 playlist.js 內無有效單字資料。");
                    }}
                }};
                document.head.appendChild(script);
            }}
        }}

        function showError(msg) {{
            displayWord.innerText = "⚠️ 載入錯誤";
            displayMeaning.innerText = msg;
            displayMeaning.style.color = "#ef4444";
        }}

        // 初始化播放清單 UI
        function initPlaylist() {{
            playlistUi.innerHTML = '';
            
            // 防呆設定跳轉範圍
            jumpInput.max = rawPlaylist.length;
            jumpInput.placeholder = `1-${{rawPlaylist.length}}`;

            if (activePlaylist.length === 0) {{
                playlistUi.innerHTML = `
                    <div class="empty-search">
                        <i class="fa-solid fa-folder-open"></i>
                        沒有找到任何符合的單字
                    </div>
                `;
                return;
            }}

            activePlaylist.forEach((item, index) => {{
                // 取得其在原始陣列中的索引
                const originalIndex = activeIndices[index];
                const li = document.createElement('li');
                li.id = 'track-' + originalIndex;
                li.onclick = () => loadTrack(originalIndex);
                
                li.innerHTML = `
                    <span class="track-num">${{originalIndex + 1}}</span>
                    <div class="track-content">
                        <span class="track-word">${{item.word}}</span>
                        <span class="track-meaning">${{item.meaning}}</span>
                    </div>
                `;
                playlistUi.appendChild(li);
            }});
            
            // 重新為當前歌曲標記高亮樣式
            highlightActiveTrack();
        }}

        // 搜尋篩選過濾邏輯
        function filterPlaylist() {{
            const query = searchInput.value.toLowerCase().trim();
            
            if (!query) {{
                activePlaylist = [...rawPlaylist];
                activeIndices = rawPlaylist.map((_, i) => i);
            }} else {{
                activePlaylist = [];
                activeIndices = [];
                rawPlaylist.forEach((item, index) => {{
                    const wordMatch = item.word.toLowerCase().includes(query);
                    const meaningMatch = item.meaning.toLowerCase().includes(query);
                    if (wordMatch || meaningMatch) {{
                        activePlaylist.push(item);
                        activeIndices.push(index);
                    }}
                }});
            }}
            initPlaylist();
        }}
        
        // 標記目前高亮曲目並自動平滑滾動
        function highlightActiveTrack() {{
            document.querySelectorAll('.playlist li').forEach(el => el.classList.remove('active'));
            const activeItem = document.getElementById('track-' + currentIndex);
            
            if (activeItem) {{
                activeItem.classList.add('active');
                
                // 平滑滾動讓當前音軌保持在固定 header 下方適當位置，避免被毛玻璃面板遮擋
                const header = document.querySelector('.player-header');
                const headerHeight = header ? header.offsetHeight : 380;
                
                const elementRect = activeItem.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const targetScrollTop = absoluteElementTop - headerHeight - 20;

                window.scrollTo({{
                    top: targetScrollTop,
                    behavior: 'smooth'
                }});
            }}
        }}
        
        // 清理目前所有間隔狀態
        function clearGapState() {{
            if (gapTimer) {{ 
                clearTimeout(gapTimer); 
                gapTimer = null; 
            }}
            if (restIntervalId) {{
                clearInterval(restIntervalId);
                restIntervalId = null;
            }}
            isGapPaused = false;
            gapRemaining = 0;
            appBody.classList.remove('resting-state');
        }}

        // 載入特定索引的音軌
        function loadTrack(index) {{
            clearGapState();
            if (index < 0 || index >= rawPlaylist.length) return;
            
            currentIndex = index;
            const item = rawPlaylist[currentIndex];

            audio.src = item.file;
            displayWord.innerText = item.word;
            displayMeaning.innerText = item.meaning;
            displaySentence.innerText = item.sentence || ""; 
            displaySentenceTrans.innerText = item.sentence_trans || "";

            highlightActiveTrack();
            
            // 重置播放次數為第一遍
            currentPlayCount = 1;
            
            audio.play().catch(e => {{}});
        }}

        // 播放與暫停切換主核心
        function togglePlay() {{
            if (gapTimer) {{
                pauseGap();
            }} else if (isGapPaused) {{
                resumeGap();
            }} else {{
                audio.paused ? audio.play() : audio.pause();
            }}
        }}

        audio.onplay = () => {{
            clearGapState();
            playPauseBtn.innerHTML = '<i class="fa-solid fa-pause"></i> 暫停';
        }};
        
        audio.onpause = () => {{
            if (!isGapPaused) {{
                playPauseBtn.innerHTML = '<i class="fa-solid fa-play"></i> 播放';
            }}
        }};
        
        // 啟動單字間的休息時間倒數
        function startGap(seconds) {{
            clearGapState(); 
            gapRemaining = seconds * 1000;
            appBody.classList.add('resting-state');
            resumeGap();
        }}
        
        // 恢復倒數
        function resumeGap() {{
            isGapPaused = false;
            gapStartTime = Date.now();
            appBody.classList.add('resting-state');
            
            // 啟用秒數視覺倒數更新器
            updateRestBtnText();
            restIntervalId = setInterval(updateRestBtnText, 100);
            
            gapTimer = setTimeout(() => {{
                clearGapState();
                playNext();
            }}, gapRemaining);
        }}
        
        // 暫停倒數
        function pauseGap() {{
            if (!gapTimer) return;
            isGapPaused = true;
            clearTimeout(gapTimer);
            gapTimer = null;
            if (restIntervalId) {{
                clearInterval(restIntervalId);
                restIntervalId = null;
            }}
            const elapsed = Date.now() - gapStartTime;
            gapRemaining -= elapsed;
            playPauseBtn.innerHTML = `<i class="fa-solid fa-forward-step"></i> 繼續 (${{(gapRemaining / 1000).toFixed(1)}}s)`;
        }}

        // 更新間隔倒數時的按鈕文字
        function updateRestBtnText() {{
            const elapsed = Date.now() - gapStartTime;
            const currentLeft = Math.max(0, gapRemaining - elapsed);
            playPauseBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> 休息 (${{(currentLeft / 1000).toFixed(1)}}s)`;
        }}

        // 精準跳转至指定單字編號
        function jumpToTrack() {{
            const val = parseInt(jumpInput.value);
            if (!val || val < 1 || val > rawPlaylist.length) {{
                alert("請輸入 1 到 " + rawPlaylist.length + " 之間的正確單字編號");
                return;
            }}
            loadTrack(val - 1);
            jumpInput.value = '';
        }}

        jumpInput.addEventListener("keydown", (e) => {{
            if (e.key === "Enter") jumpToTrack();
        }});

        // 播放下一首
        function playNext(force = false) {{
            if (force) clearGapState();

            if (currentIndex < rawPlaylist.length - 1) {{
                loadTrack(currentIndex + 1);
            }} else {{
                clearGapState();
                displayWord.innerText = "🎉 恭喜完成！";
                displayMeaning.innerText = "所有單字皆已播放完畢";
                displaySentence.innerText = "";
                displaySentenceTrans.innerText = "";
                playPauseBtn.innerHTML = '<i class="fa-solid fa-rotate-left"></i> 重頭播放';
                playPauseBtn.onclick = () => {{
                    playPauseBtn.onclick = togglePlay;
                    loadTrack(0);
                }};
            }}
        }}
        
        // 播放上一首
        function playPrev() {{
            if (currentIndex > 0) {{
                loadTrack(currentIndex - 1);
            }}
        }}

        // 單曲播放結束，觸發重複播放或間隔休息
        audio.addEventListener('ended', () => {{
            const repeatVal = parseInt(document.getElementById('repeatInput').value) || 1;
            if (currentPlayCount < repeatVal) {{
                currentPlayCount++;
                audio.currentTime = 0;
                audio.play().catch(e => {{}});
            }} else {{
                const delayVal = parseFloat(delayInput.value) || 0;
                if (delayVal <= 0) {{
                    playNext();
                }} else {{
                    startGap(delayVal);
                }}
            }}
        }});

        // 全域鍵盤快捷鍵綁定
        document.addEventListener('keydown', (e) => {{
            // 若游標位於輸入框內則不觸發快捷鍵，避免打字干擾
            if (document.activeElement.tagName === "INPUT") return;

            if (e.code === "Space") {{
                e.preventDefault();
                togglePlay();
            }} else if (e.code === "ArrowLeft") {{
                playPrev();
            }} else if (e.code === "ArrowRight") {{
                playNext(true);
            }}
        }});

        // 載入第一首曲目（但不自動播放，符合現代瀏覽器限制與使用者習慣）
        function initPlayer() {{
            initPlaylist();
            if (rawPlaylist.length > 0) {{
                const first = rawPlaylist[0];
                audio.src = first.file;
                displayWord.innerText = first.word;
                displayMeaning.innerText = first.meaning;
                displaySentence.innerText = first.sentence || "";
                displaySentenceTrans.innerText = first.sentence_trans || "";
                highlightActiveTrack();
            }}
        }}

        // 啟動加載程序
        loadDataAndInit();
    </script>
</body>
</html>
"""

    with open(HTML_FILE, "w", encoding="utf-8") as html_f:
        html_f.write(html_content)
    print(f"✅ 網頁引擎生成完成！已產出: {HTML_FILE}")

    # 3. 寫入高質感純閱讀清單 mp3.html 檔案 (不含播放器)
    html_read_content = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字搭配短語閱讀清單</title>
    <!-- 載入 Google Fonts 設計字體與 Font Awesome 6 圖示 -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {
            --bg-color: #0f172a;
            --surface-color: rgba(30, 41, 59, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --primary-color: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.15);
            --text-main: #f8fafc;
            --text-dim: #94a3b8;
            --transition: all 0.2s ease;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background-color: var(--bg-color);
            background-image:
                radial-gradient(circle at 10% 10%, rgba(99, 102, 241, 0.1) 0%, transparent 40%),
                radial-gradient(circle at 90% 90%, rgba(236, 72, 153, 0.05) 0%, transparent 40%);
            color: var(--text-main);
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            min-height: 100vh;
            padding: 0;
        }

        .container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        header {
            position: sticky;
            top: 0;
            background: rgba(15, 23, 42, 0.8);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            padding: 20px 0;
            z-index: 100;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 20px;
        }

        h1 {
            font-family: 'Outfit', sans-serif;
            font-size: 1.6rem;
            font-weight: 700;
            background: linear-gradient(135deg, #fff 40%, var(--primary-color) 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        h1 i {
            color: var(--primary-color);
            -webkit-text-fill-color: initial;
        }

        .stats {
            font-size: 0.85rem;
            color: var(--text-dim);
            background: rgba(255, 255, 255, 0.05);
            padding: 4px 12px;
            border-radius: 20px;
            border: 1px solid var(--border-color);
        }

        .search-wrapper {
            position: relative;
            width: 100%;
            max-width: 400px;
        }

        .search-wrapper i {
            position: absolute;
            left: 12px;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-dim);
        }

        #search-input {
            width: 100%;
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border-color);
            color: #fff;
            padding: 10px 12px 10px 36px;
            border-radius: 10px;
            font-size: 0.9rem;
            outline: none;
            transition: var(--transition);
        }

        #search-input:focus {
            border-color: var(--primary-color);
            box-shadow: 0 0 10px var(--primary-glow);
        }

        /* 表格排版 */
        .table-container {
            background: var(--surface-color);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th {
            background: rgba(30, 41, 59, 0.9);
            font-family: 'Outfit', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-main);
            padding: 14px 16px;
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 10;
        }

        td {
            padding: 14px 16px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.95rem;
            vertical-align: top;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr {
            transition: var(--transition);
        }

        tr:hover {
            background: rgba(99, 102, 241, 0.04);
        }

        .col-no {
            width: 60px;
            color: var(--text-dim);
            font-weight: 600;
            font-family: 'Outfit', sans-serif;
            text-align: center;
        }

        .col-word {
            width: 220px;
            font-weight: 700;
            color: #fff;
            word-break: break-word;
        }

        .col-meaning {
            width: 220px;
            font-weight: 600;
            color: #818cf8;
            word-break: break-word;
        }

        .col-sentence {
            color: var(--text-dim);
            font-style: italic;
            word-break: break-word;
        }

        .col-trans {
            color: rgba(148, 163, 184, 0.7);
            word-break: break-word;
            margin-top: 4px;
            font-style: normal;
        }

        /* 找不到結果 */
        .no-results {
            text-align: center;
            padding: 40px;
            color: var(--text-dim);
            font-size: 1rem;
        }

        .no-results i {
            font-size: 2.5rem;
            margin-bottom: 12px;
            color: rgba(255, 255, 255, 0.1);
            display: block;
        }

        @media (max-width: 768px) {
            th, td {
                padding: 10px 12px;
            }
            .header-content {
                flex-direction: column;
                align-items: flex-start;
            }
            .search-wrapper {
                max-width: 100%;
            }
            table, thead, tbody, th, td, tr {
                display: block;
            }
            thead {
                display: none;
            }
            tr {
                border-bottom: 1px solid var(--border-color);
                padding: 15px 10px;
            }
            td {
                border: none;
                padding: 4px 0;
                width: 100% !important;
            }
            .col-no {
                font-size: 0.8rem;
                text-align: left;
            }
            .col-word {
                font-size: 1.1rem;
            }
            .col-meaning {
                font-size: 0.95rem;
            }
            .col-trans {
                margin-top: 2px;
            }
        }
    </style>
</head>
<body>
    <header>
        <div class="header-content">
            <h1><i class="fa-solid fa-book-open"></i> 單字搭配短語閱讀清單</h1>
            <div class="stats" id="stats-display">載入中...</div>
            <div class="search-wrapper">
                <i class="fa-solid fa-magnifying-glass"></i>
                <input type="text" id="search-input" placeholder="在清單中搜尋短語、中文或例句..." oninput="onSearch()">
            </div>
        </div>
    </header>

    <div class="container">
        <div class="table-container" id="list-container">
            <table>
                <thead>
                    <tr>
                        <th class="col-no">No.</th>
                        <th class="col-word">英文短語</th>
                        <th class="col-meaning">中文翻譯</th>
                        <th class="col-sentence">常用搭配句與中譯</th>
                    </tr>
                </thead>
                <tbody id="table-body">
                    <!-- JavaScript 將動態填入內容 -->
                </tbody>
            </table>
        </div>
    </div>

    <!-- 載入外部資料檔 -->
    <script>
        // 優先載入外部的 playlist.js
        const urlParams = new URLSearchParams(window.location.search);
        const packName = urlParams.get('pack') || '';
        
        let playlistData = [];

        function init() {
            const script = document.createElement('script');
            script.src = packName ? `${encodeURIComponent(packName)}/playlist.js` : 'playlist.js';
            script.onload = () => {
                if (window.playlistData && window.playlistData.length > 0) {
                    playlistData = window.playlistData;
                    renderTable(playlistData);
                } else {
                    showError("清單內無有效資料。");
                }
            };
            script.onerror = () => {
                showError("無法載入 playlist.js，請確認檔案是否存在。");
            };
            document.head.appendChild(script);
        }

        function showError(msg) {
            document.getElementById('stats-display').innerText = "⚠️ 錯誤";
            document.getElementById('table-body').innerHTML = `
                <tr>
                    <td colspan="4" class="no-results">
                        <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
                        ${msg}
                    </td>
                </tr>
            `;
        }

        function renderTable(data) {
            const tbody = document.getElementById('table-body');
            const stats = document.getElementById('stats-display');
            
            stats.innerText = `共計 ${data.length.toLocaleString()} 個項目`;

            if (data.length === 0) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="4" class="no-results">
                            <i class="fa-solid fa-face-frown"></i>
                            沒有找到符合搜尋條件的項目
                        </td>
                    </tr>
                `;
                return;
            }

            const fragment = document.createDocumentFragment();
            data.forEach((item, index) => {
                const tr = document.createElement('tr');
                
                // 取得原 playlist 中的序號（從 file 名稱中提取，或直接使用 index + 1）
                let displayNum = index + 1;
                const fileMatch = item.file.match(/_(\\d{4})_/);
                if (fileMatch) {
                    displayNum = parseInt(fileMatch[1]);
                } else {
                    const numMatch = item.file.match(/(\\d{4})_/);
                    if (numMatch) {
                        displayNum = parseInt(numMatch[1]);
                    }
                }

                tr.innerHTML = `
                    <td class="col-no">${displayNum}</td>
                    <td class="col-word">${escapeHtml(item.word)}</td>
                    <td class="col-meaning">${escapeHtml(item.meaning)}</td>
                    <td class="col-sentence">
                        <div>${escapeHtml(item.sentence || '')}</div>
                        <div class="col-trans">${escapeHtml(item.sentence_trans || '')}</div>
                    </td>
                `;
                fragment.appendChild(tr);
            });

            tbody.innerHTML = '';
            tbody.appendChild(fragment);
        }

        function onSearch() {
            const query = document.getElementById('search-input').value.toLowerCase().trim();
            if (!query) {
                renderTable(playlistData);
                return;
            }

            const filtered = playlistData.filter(item => {
                return item.word.toLowerCase().includes(query) ||
                       item.meaning.toLowerCase().includes(query) ||
                       (item.sentence && item.sentence.toLowerCase().includes(query)) ||
                       (item.sentence_trans && item.sentence_trans.toLowerCase().includes(query));
            });

            renderTable(filtered);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        }

        init();
    </script>
</body>
</html>
"""

    with open(READ_HTML_FILE, "w", encoding="utf-8") as read_f:
        read_f.write(html_read_content)
    print(f"✅ 閱讀清單網頁生成完成！已產出: {READ_HTML_FILE}")
    print("🚀 引擎與資料解耦重構完成！雙擊 player.html 即可在本地端執行。")

if __name__ == "__main__":
    generate_player()
