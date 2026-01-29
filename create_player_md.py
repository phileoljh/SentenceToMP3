import os
import json
import re

# =================設定區=================
MP3_DIR = "MP3_Output"       # MP3 音檔資料夾 (請確認與產音檔腳本的輸出一致)
INPUT_FILE = "mp3.md"        # 來源 Markdown 檔案
HTML_FILE = "player_v5.html" # 產出的網頁檔名
# ========================================

def parse_md_file(filepath):
    """
    解析 mp3.md (Markdown 表格格式)
    格式範例: | 1. succinct | 簡潔的 | Keep your explanation... | ... |
    """
    word_data = []
    
    if not os.path.exists(filepath):
        print(f"⚠️ 警告：找不到 {filepath}，網頁將只顯示檔名。")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            # 過濾無效行：不以 | 開頭、或是表頭分隔線
            if not line.startswith("|") or "---" in line or "English" in line:
                continue

            # 切割欄位 (去除空字串)
            parts = [p.strip() for p in line.split('|') if p.strip()]

            # 確保欄位足夠 (至少要有 單字 和 中文)
            if len(parts) >= 2:
                # 1. 處理英文單字 (移除序號 "1. ")
                raw_word = parts[0]
                clean_word = re.sub(r'^\d+\.\s*', '', raw_word)

                # 2. 處理中文
                meaning = parts[1]

                # 3. 處理例句 (如果有第三欄)
                sentence = parts[2] if len(parts) >= 3 else ""

                word_data.append({
                    "word": clean_word,
                    "meaning": meaning,
                    "sentence": sentence
                })
    
    return word_data

def generate_html():
    # 1. 掃描 MP3
    if not os.path.exists(MP3_DIR):
        print(f"❌ 找不到 {MP3_DIR} 資料夾")
        return

    # 讀取並排序 (確保 0001, 0002... 順序正確)
    mp3_files = [f for f in os.listdir(MP3_DIR) if f.lower().endswith('.mp3')]
    mp3_files.sort() 

    if not mp3_files:
        print("⚠️ 資料夾內沒有 MP3 檔案")
        return

    # 2. 讀取 MD 資料
    text_data = parse_md_file(INPUT_FILE)

    # 3. 合併資料
    playlist = []
    
    # 以 MP3 檔案為主體，去對應文字資料
    for i, filename in enumerate(mp3_files):
        # 預設值 (如果沒有對應的文字資料)
        item = {
            "file": f"{MP3_DIR}/{filename}",
            "word": filename.replace(".mp3", ""), # 預設用檔名
            "meaning": "",
            "sentence": ""
        }
        
        # 如果 index 在文字資料範圍內，則覆蓋資訊
        if i < len(text_data):
            item["word"] = text_data[i]["word"]
            item["meaning"] = text_data[i]["meaning"]
            item["sentence"] = text_data[i]["sentence"]
            
        playlist.append(item)

    js_playlist = json.dumps(playlist, ensure_ascii=False)

    # 4. 生成 HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字學習播放器 V5</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #f4f4f9; color: #333; }}
        
        /* 播放器控制區 (固定在頂部) */
        .player-header {{ 
            position: sticky; 
            top: 0; 
            background: #fff; 
            padding: 15px 20px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.08); 
            z-index: 100; 
            border-bottom-left-radius: 15px;
            border-bottom-right-radius: 15px;
        }}
        
        h2 {{ margin: 0 0 10px 0; font-size: 1.2rem; text-align: center; color: #444; }}

        /* 目前播放資訊 */
        #current-info {{ text-align: center; margin-bottom: 15px; min-height: 4.5em; display: flex; flex-direction: column; justify-content: center; }}
        #current-word {{ font-size: 1.6em; font-weight: bold; color: #007bff; line-height: 1.2; margin-bottom: 5px; }}
        #current-meaning {{ font-size: 1.1em; color: #333; font-weight: 500; }}
        #current-sentence {{ font-size: 0.9em; color: #666; margin-top: 5px; font-style: italic; display: block; }}
        
        audio {{ width: 100%; margin-bottom: 10px; }}

        /* 按鈕群組 */
        .btn-group {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 15px; }}
        button {{ padding: 10px 20px; border: none; background: #eef2f5; border-radius: 8px; cursor: pointer; font-size: 1rem; color: #555; transition: 0.2s; }}
        button:active {{ background: #dce4eb; transform: scale(0.98); }}
        #playPauseBtn {{ background: #007bff; color: white; min-width: 100px; font-weight: bold; }}

        /* 設定面板 */
        .controls-panel {{ display: flex; justify-content: center; gap: 15px; font-size: 0.9em; color: #666; background: #f8f9fa; padding: 10px; border-radius: 8px; }}
        .control-item input {{ padding: 5px; text-align: center; border: 1px solid #ddd; border-radius: 4px; width: 50px; }}
        
        /* 播放清單 */
        .playlist-container {{ padding: 20px; padding-bottom: 300px; /* 底部留白，方便閱讀最後幾項 */ }}
        .playlist {{ list-style: none; padding: 0; margin: 0; }}
        .playlist li {{ 
            padding: 15px; 
            margin-bottom: 10px;
            background: #fff; 
            border-radius: 10px; 
            cursor: pointer; 
            display: flex; 
            align-items: center; 
            transition: 0.2s; 
            border: 1px solid transparent;
        }}
        .playlist li:hover {{ transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        
        /* 正在播放的項目樣式 */
        .playlist li.active {{ 
            background-color: #e7f1ff; 
            border-color: #007bff; 
            box-shadow: 0 4px 12px rgba(0,123,255,0.15);
        }}

        .track-num {{ font-size: 0.9em; color: #999; width: 40px; text-align: center; flex-shrink: 0; }}
        .track-content {{ flex-grow: 1; margin-left: 10px; }}
        .track-word {{ font-weight: bold; font-size: 1.1em; color: #222; display: block; }}
        .track-meaning {{ font-size: 0.95em; color: #666; }}
        .active .track-word {{ color: #007bff; }}
        
    </style>
</head>
<body>

    <div class="player-header">
        <h2>🎧 單字聽力訓練 V5</h2>
        
        <div id="current-info">
            <span id="current-word">Loading...</span>
            <span id="current-meaning"></span>
            <span id="current-sentence"></span>
        </div>

        <audio id="audioPlayer" controls></audio>
        
        <div class="btn-group">
            <button onclick="playPrev()">⏮</button>
            <button id="playPauseBtn" onclick="togglePlay()">▶ 播放</button>
            <button onclick="playNext(true)">⏭</button>
        </div>

        <div class="controls-panel">
            <div class="control-item">
                <label>間隔(秒)</label>
                <input type="number" id="delayInput" value="1.0" min="0" step="0.5">
            </div>
            <div class="control-item">
                <label>跳至</label>
                <input type="number" id="jumpInput" placeholder="No.">
                <button onclick="jumpToTrack()" style="padding: 4px 10px; background: #ddd; color: #333;">Go</button>
            </div>
        </div>
    </div>

    <div class="playlist-container">
        <ul class="playlist" id="playlist-ui"></ul>
    </div>

    <script>
        const playlistData = {js_playlist};

        let currentIndex = 0;
        let waitTimer = null; 

        const audio = document.getElementById('audioPlayer');
        const displayWord = document.getElementById('current-word');
        const displayMeaning = document.getElementById('current-meaning');
        const displaySentence = document.getElementById('current-sentence');
        const playlistUi = document.getElementById('playlist-ui');
        const delayInput = document.getElementById('delayInput');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const jumpInput = document.getElementById('jumpInput');

        // 初始化播放清單
        function initPlaylist() {{
            playlistUi.innerHTML = '';
            playlistData.forEach((item, index) => {{
                const li = document.createElement('li');
                li.id = 'track-' + index;
                li.onclick = () => loadTrack(index);
                
                li.innerHTML = `
                    <span class="track-num">${{index + 1}}</span>
                    <div class="track-content">
                        <span class="track-word">${{item.word}}</span>
                        <span class="track-meaning">${{item.meaning}}</span>
                    </div>
                `;
                playlistUi.appendChild(li);
            }});
        }}

        // 載入並播放音軌
        function loadTrack(index) {{
            if (waitTimer) {{ clearTimeout(waitTimer); waitTimer = null; }}
            if (index < 0 || index >= playlistData.length) return;
            
            currentIndex = index;
            const item = playlistData[currentIndex];

            // 更新播放器資訊
            audio.src = item.file;
            displayWord.innerText = item.word;
            displayMeaning.innerText = item.meaning;
            displaySentence.innerText = item.sentence || ""; // 顯示例句

            // 更新清單樣式
            document.querySelectorAll('.playlist li').forEach(el => el.classList.remove('active'));
            const activeItem = document.getElementById('track-' + currentIndex);
            
            if(activeItem) {{
                activeItem.classList.add('active');
                
                // === ⭐️ 關鍵修改：自定義捲動位置 ===
                // 目標：將 activeItem 捲動到視窗高度的 75% 處 (下方 1/4)
                // 這樣上方大面積的控制面板就不會遮住它
                
                const elementRect = activeItem.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                // 計算目標捲動位置 = 元素絕對位置 - (視窗高度 * 0.75)
                const targetScrollTop = absoluteElementTop - (window.innerHeight * 0.75);

                window.scrollTo({{
                    top: targetScrollTop,
                    behavior: 'smooth'
                }});
            }}
            
            audio.play().catch(e => {{ /* 忽略自動播放限制錯誤 */ }});
        }}

        // 播放控制
        function togglePlay() {{
            audio.paused ? audio.play() : audio.pause();
        }}
        audio.onplay = () => playPauseBtn.innerText = "⏸ 暫停";
        audio.onpause = () => playPauseBtn.innerText = "▶ 播放";

        // 跳轉功能
        function jumpToTrack() {{
            const val = parseInt(jumpInput.value);
            if (!val || val < 1 || val > playlistData.length) return;
            loadTrack(val - 1);
            jumpInput.value = '';
        }}

        // 下一首邏輯
        function playNext(force = false) {{
            if (force && waitTimer) clearTimeout(waitTimer);

            if (currentIndex < playlistData.length - 1) {{
                loadTrack(currentIndex + 1);
            }} else {{
                // 播放結束
                displayWord.innerText = "🎉 完成";
                displayMeaning.innerText = "所有單字已播放完畢";
                displaySentence.innerText = "";
            }}
        }}
        
        function playPrev() {{
            if (currentIndex > 0) loadTrack(currentIndex - 1);
        }}

        // 監聽播放結束 -> 延遲 -> 下一首
        audio.addEventListener('ended', () => {{
            const delayVal = parseFloat(delayInput.value) || 0;
            if (delayVal <= 0) {{
                playNext();
            }} else {{
                waitTimer = setTimeout(() => playNext(), delayVal * 1000);
            }}
        }});

        // 啟動
        initPlaylist();
        // 預載第一首但不播放
        const firstItem = playlistData[0];
        audio.src = firstItem.file;
        displayWord.innerText = firstItem.word;
        displayMeaning.innerText = firstItem.meaning;
        displaySentence.innerText = firstItem.sentence || "";

    </script>
</body>
</html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ 網頁生成完畢！檔案: {HTML_FILE}")
    print("👉 請確認您的 MP3 資料夾名稱是否正確 (預設為 MP3_Output)")

if __name__ == "__main__":
    generate_html()