import asyncio
import edge_tts
import os
import re

# =================設定區=================
INPUT_FILE = "mp3.md"        # 輸入的 Markdown 檔案
OUTPUT_DIR = "MP3_Output"    # 輸出的資料夾名稱

# 語音設定
VOICE_EN_WORD = "en-US-AndrewNeural"     # 美式男聲 (唸單字)
VOICE_EN_SENT = "en-US-AriaNeural"       # 美式女聲 (唸例句)
VOICE_ZH = "zh-TW-HsiaoChenNeural"       # 台灣女聲 (唸中文)
"""
VOICE_EN = "en-US-AndrewNeural"      # 美式男聲
VOICE_ZH = "zh-TW-HsiaoChenNeural"   # 台灣女聲

ShortName (ID),性別,特色描述
en-US-AndrewNeural,男聲,溫暖、專業，適合解說（您原本選用的）
en-US-AriaNeural,女聲,微軟預設，非常自然，適用各種情境
en-US-GuyNeural,男聲,一般對話感強
en-US-JennyNeural,女聲,類似 Aria 但語調略有不同
en-US-ChristopherNeural,男聲,聲音較低沉厚實
en-US-EricNeural,男聲,語速稍快，較為年輕

zh-TW-HsiaoChenNeural,女聲,最通用，聲音清晰自然（您原本選用的）
zh-TW-YunJheNeural,男聲,沉穩，適合新聞或長文朗讀
zh-TW-HsiaoYuNeural,女聲,較為年輕、輕快，適合輕鬆內容
"""

# ⭐️ 模式選擇 (在此切換) ⭐️
# 1 = 僅單字 + 中文 (Word + Chinese)
# 2 = 單字 + 中文 + 英文例句 (Word + Chinese + Example Sentence)
AUDIO_MODE = 2 
# ========================================

async def get_audio_bytes(text, voice):
    """呼叫 edge-tts 生成語音並回傳二進位資料"""
    content = b""
    try:
        communicate = edge_tts.Communicate(text, voice)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                content += chunk["data"]
    except Exception as e:
        print(f"   ⚠️ 語音生成錯誤 [{text}]: {e}")
    return content

async def process_line(index, line, semaphore):
    """處理單一行 Markdown 表格資料"""
    async with semaphore:
        # 1. 預處理：去除前後空白
        line = line.strip()
        
        # 2. 過濾無效行 (空行、表頭、分隔線)
        if not line.startswith("|"): return
        if "English" in line and "中文" in line: return  # 過濾表頭
        if "---" in line: return  # 過濾分隔線

        # 3. 解析表格欄位
        # Markdown 表格通常以 | 分隔，split後頭尾會產生空字串，故需過濾
        parts = [p.strip() for p in line.split('|') if p.strip()]
        
        # 確保欄位數量足夠 (序號單字, 中文, 例句, 中譯) 至少要有前兩個
        if len(parts) < 2:
            return

        # 4. 提取資料
        raw_word_col = parts[0]  # 第一欄：(序號) English
        zh_def = parts[1]        # 第二欄：中文
        
        # 提取例句 (如果有的話，且模式需要)
        en_sentence = ""
        if len(parts) >= 3:
            en_sentence = parts[2] # 第三欄：常用搭配句

        # 5. 清理單字 (去除序號 "1. ", "2. " 等)
        # Regex: 抓取開頭的數字加點，並替換為空
        en_word = re.sub(r'^\d+\.\s*', '', raw_word_col)

        if not en_word: return

        # 6. 決定檔名 (4位數序號)
        safe_filename_text = re.sub(r'[\\/*?:"<>|]', "", en_word)
        filename = f"{index:04d}_{safe_filename_text}.mp3"
        filepath = os.path.join(OUTPUT_DIR, filename)

        if os.path.exists(filepath):
            print(f"⏩ 跳過已存在 [{index:04d}]: {en_word}")
            return

        print(f"處理中 [{index:04d}]: {en_word}")

        # 7. 依據模式生成語音片段
        audio_segments = []
        
        # 片段 A: 單字
        audio_segments.append(await get_audio_bytes(en_word, VOICE_EN_WORD))
        
        # 片段 B: 中文釋義
        if zh_def:
            audio_segments.append(await get_audio_bytes(zh_def, VOICE_ZH))

        # 片段 C: 英文例句 (僅模式 2 且有例句時)
        if AUDIO_MODE == 2 and en_sentence and en_sentence != "":
            audio_segments.append(await get_audio_bytes(en_sentence, VOICE_EN_SENT))

        # 8. 寫入檔案 (合併所有片段)
        try:
            with open(filepath, "wb") as out_f:
                for segment in audio_segments:
                    out_f.write(segment)
        except Exception as e:
            print(f"❌ 寫入失敗: {e}")

async def main():
    # 建立輸出目錄
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"已建立目錄: {OUTPUT_DIR}")
    
    # 檢查輸入檔案
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到 {INPUT_FILE}，請確認檔案名稱是否正確。")
        return

    print(f"正在讀取 {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 限制並發數，避免請求過快被封鎖
    semaphore = asyncio.Semaphore(5)
    tasks = []
    
    valid_count = 0
    for line in lines:
        # 簡單預判是否為資料行，用於計算序號
        if not line.strip().startswith("|"): continue
        if "(序號) English" in line or "---" in line: continue
        
        valid_count += 1
        task = process_line(valid_count, line, semaphore)
        tasks.append(task)

    if tasks:
        print(f"開始處理 {len(tasks)} 筆資料，模式: {AUDIO_MODE} ...")
        await asyncio.gather(*tasks)
        print(f"\n✅ 全部完成！檔案已儲存於 {OUTPUT_DIR} 資料夾。")
    else:
        print("沒有偵測到有效的表格資料。")

if __name__ == "__main__":
    asyncio.run(main())