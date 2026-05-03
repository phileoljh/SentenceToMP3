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

async def get_audio_bytes(text, voice, max_retries=3, delay=2):
    """呼叫 edge-tts 生成語音並回傳二進位資料，包含重試機制"""
    for attempt in range(max_retries):
        content = b""
        try:
            communicate = edge_tts.Communicate(text, voice)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    content += chunk["data"]
            
            if content:
                return content
            
            # 如果跑完 loop 但 content 還是空的
            print(f"   ⚠️ 語音生成內容為空 [{text}] (第 {attempt + 1} 次嘗試)")
        except Exception as e:
            # 判斷是否為常見的網路問題或參數問題
            print(f"   ⚠️ 語音生成錯誤 [{text}]: {e} (第 {attempt + 1} 次嘗試)")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            
    print(f"   ❌ 語音生成失敗 [{text}]，已達到最大重試次數 ({max_retries})")
    return b""


def clean_text_for_tts(text):
    """
    清洗送交 TTS 的文字，防止標點符號組合成表情符號導致誤讀。
    
    原因：TTS 引擎（如 Edge TTS）會將 ";(" 或 ":)" 識別為表情符號並讀出含義。
    解決方式：在連續的標點符號中間插入空格，打破表情符號的識別特徵。
    """
    if not text:
        return ""
    
    # 使用正規表達式在連續的標點符號（非字母數字、非空白）中間插入空格
    # \1 代表匹配到的第一個字元，其後補一個空格
    # 例如：";(" 變為 "; ("
    cleaned = re.sub(r'([^\w\s])(?=[^\w\s])', r'\1 ', text)
    
    # 針對一些字母組成的常見表情符號（如 XD）也進行分隔
    cleaned = re.sub(r'([X])(?=[D])', r'\1 ', cleaned, flags=re.IGNORECASE)
    
    return cleaned


async def process_line(index, line, semaphore):
    """處理單一行 Markdown 表格資料"""
    async with semaphore:
        # 1. 預處理：去除前後空白
        line = line.strip()
        
        # 2. 過濾無效行 (空行、表頭、分隔線)
        if not line.startswith("|"): return
        if "| English |" in line or "(序號) English" in line: return  # 過濾表頭
        if "---" in line: return  # 過濾分隔線

        # 3. 解析表格欄位
        # Markdown 表格通常以 | 分隔，split後頭尾會產生空字串，故需過濾
        parts = [p.strip() for p in line.split('|')]
        # 去除 split 產生的頭尾空元素 (若表格開頭結尾都有 |)
        if parts[0] == "": parts.pop(0)
        if parts and parts[-1] == "": parts.pop()

        # 4. 偵測與提取資料 (自動相容 4 或 5 欄位)
        # 5 欄位格式: | 序號 | 英文 | 中文 | 例句 | 中文例句 | (parts 長度為 5)
        # 4 欄位格式: | (序號) 英文 | 中文 | 例句 | 中譯 | (parts 長度為 4)
        
        if len(parts) >= 5:
            # 假設為 5 欄位格式，英文在第 2 欄 (index 1)
            raw_word_col = parts[1]
            zh_def = parts[2]
            en_sentence = parts[3]
        elif len(parts) >= 2:
            # 假設為 4 欄位格式，英文在第 1 欄 (index 0)
            raw_word_col = parts[0]
            zh_def = parts[1]
            en_sentence = parts[2] if len(parts) >= 3 else ""
        else:
            return

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
        audio_segments.append(await get_audio_bytes(clean_text_for_tts(en_word), VOICE_EN_WORD))
        
        # 片段 B: 中文釋義
        if zh_def:
            audio_segments.append(await get_audio_bytes(clean_text_for_tts(zh_def), VOICE_ZH))

        # 片段 C: 英文例句 (僅模式 2 且有例句時)
        if AUDIO_MODE == 2 and en_sentence and en_sentence != "":
            audio_segments.append(await get_audio_bytes(clean_text_for_tts(en_sentence), VOICE_EN_SENT))

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
        # 過濾表頭關鍵字 (包含 4 欄與 5 欄格式)
        header_keywords = ["English", "(序號)", "序號", "英文片語", "---"]
        if any(kw in line for kw in header_keywords): continue
        
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