import os
import json
import re

# =================設定區=================
MP3_DIR = "MP3_Output"       # MP3 音檔資料夾
INPUT_FILE = "mp3.md"        # 來源 Markdown 檔案
HTML_FILE = "player_v6_fixed.html" # 產出的網頁檔名
# ========================================

def parse_md_file(filepath):
    """
    解析 mp3.md (Markdown 表格格式)
    格式: | 1. word | 中文 | 例句 | 例句中譯 |
    """
    word_data = []
    
    if not os.path.exists(filepath):
        print(f"⚠️ 警告：找不到 {filepath}，網頁將只顯示檔名。")
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            
            if not line.startswith("|") or "---" in line or "| English |" in line or "(序號) English" in line:
                continue

            parts = [p.strip() for p in line.split('|') if p.strip()]

            if len(parts) >= 2:
                raw_word = parts[0]
                clean_word = re.sub(r'^\d+\.\s*', '', raw_word)
                meaning = parts[1]
                sentence = parts[2] if len(parts) >= 3 else ""
                sentence_trans = parts[3] if len(parts) >= 4 else ""

                word_data.append({
                    "word": clean_word,
                    "meaning": meaning,
                    "sentence": sentence,
                    "sentence_trans": sentence_trans
                })
    return word_data

def generate_html():
    if not os.path.exists(MP3_DIR):
        print(f"❌ 找不到 {MP3_DIR} 資料夾")
        return

    mp3_files = [f for f in os.listdir(MP3_DIR) if f.lower().endswith('.mp3')]
    mp3_files.sort() 

    if not mp3_files:
        print("⚠️ 資料夾內沒有 MP3 檔案")
        return

    text_data = parse_md_file(INPUT_FILE)
    playlist = []
    
    import urllib.parse

    for i, filename in enumerate(mp3_files):
        # 使用 urllib.parse.quote 進行 URL 編碼，解決特殊字元 (如 %, 空白) 導致網頁無法播放的問題
        encoded_filename = urllib.parse.quote(filename)
        item = {
            "file": f"{MP3_DIR}/{encoded_filename}",
            "word": filename.replace(".mp3", ""),
            "meaning": "",
            "sentence": "",
            "sentence_trans": ""
        }
        
        if i < len(text_data):
            item["word"] = text_data[i]["word"]
            item["meaning"] = text_data[i]["meaning"]
            item["sentence"] = text_data[i]["sentence"]
            item["sentence_trans"] = text_data[i]["sentence_trans"]
            
        playlist.append(item)

    js_playlist = json.dumps(playlist, ensure_ascii=False)

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>單字聽力訓練 V6 (修正版)</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #f4f4f9; color: #333; }}
        
        .player-header {{ 
            position: sticky; top: 0; background: #fff; padding: 15px 20px; 
            box-shadow: 0 4px 15px rgba(0,0,0,0.08); z-index: 100; 
            border-bottom-left-radius: 15px; border-bottom-right-radius: 15px;
        }}
        
        h2 {{ margin: 0 0 10px 0; font-size: 1.2rem; text-align: center; color: #444; }}

        #current-info {{ text-align: center; margin-bottom: 15px; min-height: 5em; display: flex; flex-direction: column; justify-content: center; }}
        #current-word {{ font-size: 1.6em; font-weight: bold; color: #007bff; line-height: 1.2; margin-bottom: 5px; }}
        #current-meaning {{ font-size: 1.1em; color: #333; font-weight: 500; }}
        
        .sentence-box {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; }}
        #current-sentence {{ font-size: 0.95em; color: #555; font-style: italic; display: block; line-height: 1.4; }}
        #current-sentence-trans {{ font-size: 0.9em; color: #888; display: block; margin-top: 4px; }}
        
        audio {{ width: 100%; margin-bottom: 10px; margin-top: 10px; }}

        .btn-group {{ display: flex; justify-content: center; gap: 15px; margin-bottom: 15px; }}
        button {{ padding: 10px 20px; border: none; background: #eef2f5; border-radius: 8px; cursor: pointer; font-size: 1rem; color: #555; transition: 0.2s; }}
        button:active {{ background: #dce4eb; transform: scale(0.98); }}
        #playPauseBtn {{ background: #007bff; color: white; min-width: 100px; font-weight: bold; }}

        .controls-panel {{ display: flex; justify-content: center; gap: 15px; font-size: 0.9em; color: #666; background: #f8f9fa; padding: 10px; border-radius: 8px; }}
        /* 讓輸入框適合顯示數字 */
        .control-item input {{ padding: 5px; text-align: center; border: 1px solid #ddd; border-radius: 4px; width: 60px; }}
        
        .playlist-container {{ padding: 20px; padding-bottom: 350px; }}
        .playlist {{ list-style: none; padding: 0; margin: 0; }}
        .playlist li {{ 
            padding: 15px; margin-bottom: 10px; background: #fff; border-radius: 10px; 
            cursor: pointer; display: flex; align-items: center; transition: 0.2s; border: 1px solid transparent;
        }}
        .playlist li:hover {{ transform: translateY(-2px); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
        .playlist li.active {{ background-color: #e7f1ff; border-color: #007bff; box-shadow: 0 4px 12px rgba(0,123,255,0.15); }}

        .track-num {{ font-size: 0.9em; color: #999; width: 40px; text-align: center; flex-shrink: 0; }}
        .track-content {{ flex-grow: 1; margin-left: 10px; }}
        .track-word {{ font-weight: bold; font-size: 1.1em; color: #222; display: block; }}
        .track-meaning {{ font-size: 0.95em; color: #666; }}
        .active .track-word {{ color: #007bff; }}
    </style>
</head>
<body>

    <div class="player-header">
        <h2>🎧 單字聽力訓練 V6 </h2>
        
        <div id="current-info">
            <span id="current-word">Loading...</span>
            <span id="current-meaning"></span>
            
            <div class="sentence-box">
                <span id="current-sentence"></span>
                <span id="current-sentence-trans"></span>
            </div>
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
                <input type="number" id="jumpInput" placeholder="No." min="1">
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
        let gapTimer = null;
        let gapRemaining = 0;
        let gapStartTime = 0;
        let isGapPaused = false;

        const audio = document.getElementById('audioPlayer');
        const displayWord = document.getElementById('current-word');
        const displayMeaning = document.getElementById('current-meaning');
        const displaySentence = document.getElementById('current-sentence');
        const displaySentenceTrans = document.getElementById('current-sentence-trans');
        const playlistUi = document.getElementById('playlist-ui');
        const delayInput = document.getElementById('delayInput');
        const playPauseBtn = document.getElementById('playPauseBtn');
        const jumpInput = document.getElementById('jumpInput');

        function initPlaylist() {{
            playlistUi.innerHTML = '';
            
            // 修正：動態設定輸入框最大值
            jumpInput.max = playlistData.length;
            jumpInput.placeholder = `1-${{playlistData.length}}`;

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
        
        function clearGapState() {{
            if (gapTimer) {{ clearTimeout(gapTimer); gapTimer = null; }}
            isGapPaused = false;
            gapRemaining = 0;
        }}

        function loadTrack(index) {{
            clearGapState();
            if (index < 0 || index >= playlistData.length) return;
            
            currentIndex = index;
            const item = playlistData[currentIndex];

            audio.src = item.file;
            displayWord.innerText = item.word;
            displayMeaning.innerText = item.meaning;
            displaySentence.innerText = item.sentence || ""; 
            displaySentenceTrans.innerText = item.sentence_trans || "";

            // 清單捲動邏輯 (維持 V6 設定：下方 1/4 處)
            document.querySelectorAll('.playlist li').forEach(el => el.classList.remove('active'));
            const activeItem = document.getElementById('track-' + currentIndex);
            
            if(activeItem) {{
                activeItem.classList.add('active');
                
                const elementRect = activeItem.getBoundingClientRect();
                const absoluteElementTop = elementRect.top + window.pageYOffset;
                const targetScrollTop = absoluteElementTop - (window.innerHeight * 0.75);

                window.scrollTo({{
                    top: targetScrollTop,
                    behavior: 'smooth'
                }});
            }}
            
            audio.play().catch(e => {{}});
        }}

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
            playPauseBtn.innerText = "⏸ 暫停";
        }};
        audio.onpause = () => {{
            if (!isGapPaused) playPauseBtn.innerText = "▶ 播放";
        }};
        
        function startGap(seconds) {{
            clearGapState(); 
            gapRemaining = seconds * 1000;
            resumeGap();
        }}
        
        function resumeGap() {{
            isGapPaused = false;
            gapStartTime = Date.now();
            playPauseBtn.innerText = "⏸ 休息中";
            
            gapTimer = setTimeout(() => {{
                clearGapState();
                playNext();
            }}, gapRemaining);
        }}
        
        function pauseGap() {{
            if (!gapTimer) return;
            isGapPaused = true;
            clearTimeout(gapTimer);
            gapTimer = null;
            const elapsed = Date.now() - gapStartTime;
            gapRemaining -= elapsed;
            playPauseBtn.innerText = "▶ 繼續";
        }}

        function jumpToTrack() {{
            const val = parseInt(jumpInput.value);
            // 修正：增加範圍防呆機制
            if (!val || val < 1 || val > playlistData.length) {{
                alert("請輸入 1 到 " + playlistData.length + " 之間的數字");
                return;
            }}
            loadTrack(val - 1);
            jumpInput.value = '';
        }}

        // 修正：補回 Enter 鍵監聽功能
        jumpInput.addEventListener("keydown", (e) => {{
            if (e.key === "Enter") jumpToTrack();
        }});

        function playNext(force = false) {{
            if (force) clearGapState();

            if (currentIndex < playlistData.length - 1) {{
                loadTrack(currentIndex + 1);
            }} else {{
                displayWord.innerText = "🎉 完成";
                displayMeaning.innerText = "播放結束";
                displaySentence.innerText = "";
                displaySentenceTrans.innerText = "";
            }}
        }}
        
        function playPrev() {{
            if (currentIndex > 0) loadTrack(currentIndex - 1);
        }}

        audio.addEventListener('ended', () => {{
            const delayVal = parseFloat(delayInput.value) || 0;
            if (delayVal <= 0) {{
                playNext();
            }} else {{
                startGap(delayVal);
            }}
        }});

        document.addEventListener('keydown', (e) => {{
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

        initPlaylist();
        
        const first = playlistData[0];
        audio.src = first.file;
        displayWord.innerText = first.word;
        displayMeaning.innerText = first.meaning;
        displaySentence.innerText = first.sentence || "";
        displaySentenceTrans.innerText = first.sentence_trans || "";

    </script>
</body>
</html>
    """

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✅ V6 (修正版) 網頁已生成！請開啟 {HTML_FILE}")

if __name__ == "__main__":
    generate_html()