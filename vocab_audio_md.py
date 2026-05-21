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
    
    # 將斜線替換為逗號，避免 TTS 唸出「斜線」並增加停頓感
    text = text.replace("/", ",")
    
    # 使用正規表達式在連續的標點符號（非字母數字、非空白）中間插入空格
    # \1 代表匹配到的第一個字元，其後補一個空格
    # 例如：";(" 變為 "; ("
    cleaned = re.sub(r'([^\w\s])(?=[^\w\s])', r'\1 ', text)
    
    # 針對一些字母組成的常見表情符號（如 XD）也進行分隔
    cleaned = re.sub(r'([X])(?=[D])', r'\1 ', cleaned, flags=re.IGNORECASE)
    
    return cleaned


async def process_item(item, semaphore):
    """
    處理單一單字項目的非同步下載。
    
    參數:
        item: 包含單字、釋義、例句與預期路徑的項目字典。
        semaphore: 用於限制並發數的信號量。
    """
    async with semaphore:
        filepath = item["filepath"]
        index = item["index"]
        en_word = item["word"]
        zh_def = item["meaning"]
        en_sentence = item["sentence"]

        if os.path.exists(filepath):
            print(f"⏩ 跳過已存在 [{index:04d}]: {en_word}")
            return

        print(f"處理中 [{index:04d}]: {en_word}")

        # 7. 依據模式生成語音片段
        audio_segments = []
        
        # 片段 A: 單字 (核心片段)
        seg_word = await get_audio_bytes(clean_text_for_tts(en_word), VOICE_EN_WORD)
        if not seg_word:
            print(f"⚠️ 跳過處理 [{index:04d}]: 單字音軌生成失敗 ({en_word})")
            return
        audio_segments.append(seg_word)
        
        # 片段 B: 中文釋義
        if zh_def:
            seg_zh = await get_audio_bytes(clean_text_for_tts(zh_def), VOICE_ZH)
            if not seg_zh:
                print(f"⚠️ 跳過處理 [{index:04d}]: 中文釋義音軌生成失敗 ({en_word})")
                return
            audio_segments.append(seg_zh)

        # 片段 C: 英文例句 (僅模式 2 且有例句時)
        if AUDIO_MODE == 2 and en_sentence and en_sentence != "":
            seg_sent = await get_audio_bytes(clean_text_for_tts(en_sentence), VOICE_EN_SENT)
            if not seg_sent:
                print(f"⚠️ 跳過處理 [{index:04d}]: 例句音軌生成失敗 ({en_word})")
                return
            audio_segments.append(seg_sent)

        # 8. 寫入檔案 (合併所有片段)
        total_audio = b"".join(audio_segments)
        try:
            with open(filepath, "wb") as out_f:
                out_f.write(total_audio)
        except Exception as e:
            print(f"❌ 寫入失敗 [{index:04d}]: {e}")

async def main():
    # 建立輸出目錄
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"已建立目錄: {OUTPUT_DIR}")
    
    # 檢查輸入檔案
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 找不到 {INPUT_FILE}，請確認檔案名稱是否正確。")
        return

    print(f"正在讀取與解析 {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 1. 預先解析所有有效的資料行，排除表頭
    parsed_items = []
    valid_count = 0
    
    for line in lines:
        line_strip = line.strip()
        # 僅處理 Markdown 表格資料行
        if not line_strip.startswith("|"):
            continue
        # 排除分隔線
        if "---" in line_strip:
            continue
            
        parts = [p.strip() for p in line_strip.split('|')]
        # 去除 split 產生的頭尾空元素 (若表格開頭結尾都有 |)
        if parts[0] == "":
            parts.pop(0)
        if parts and parts[-1] == "":
            parts.pop()
            
        # 偵測並相容 4 欄或 5 欄格式
        if len(parts) >= 5:
            # 5 欄位格式: | 序號 | 英文 | 中文 | 例句 | 中文例句 |
            raw_word_col = parts[1]
            zh_def = parts[2]
            en_sentence = parts[3]
        elif len(parts) >= 2:
            # 4 欄位格式: | (序號) 英文 | 中文 | 例句 | 中譯 |
            raw_word_col = parts[0]
            zh_def = parts[1]
            en_sentence = parts[2] if len(parts) >= 3 else ""
        else:
            continue
            
        # 清理單字開頭的數字序號
        en_word = re.sub(r'^\d+\.\s*', '', raw_word_col)
        if not en_word:
            continue
            
        # 表頭關鍵字精確比對，避免誤殺例句中包含 English 的一般資料行 (如 be proficient in)
        header_vals = ["(序號) English", "English", "序號", "英文片語", "英文", "word", "序號 English"]
        if en_word in header_vals:
            continue
            
        valid_count += 1
        safe_filename_text = re.sub(r'[\\/*?:"<>|]', "", en_word)
        filename = f"{valid_count:04d}_{safe_filename_text}.mp3"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        parsed_items.append({
            "index": valid_count,
            "word": en_word,
            "meaning": zh_def,
            "sentence": en_sentence,
            "filename": filename,
            "filepath": filepath,
            "safe_word": safe_filename_text
        })

    if not parsed_items:
        print("沒有偵測到有效的表格資料。")
        return

    # 2. 進行本機同步重命名優化 (快取比對)
    # 比對邏輯：如果某單字預期的 filepath 不存在，則在本機掃描是否有其他序號的同名音檔 (後綴一致)。
    # 如果有，則直接 rename 為當前序號檔名，瞬間完成而無須重新下載。
    print("🔍 啟動本機快取比對與重命名優化...")
    existing_files = [f for f in os.listdir(OUTPUT_DIR) if f.lower().endswith('.mp3')]
    claimed_physical_files = set()
    
    # 第一輪：先把完全符合目前預期檔名的實體檔案標記為 claimed，避免其被誤做改名來源
    for item in parsed_items:
        if os.path.exists(item["filepath"]):
            claimed_physical_files.add(item["filename"])
            
    # 第二輪：對於需要但不存在的檔名，嘗試尋找其他序號的同名檔案來重命名
    renamed_count = 0
    for item in parsed_items:
        if item["filename"] in claimed_physical_files:
            continue
            
        # 尋找後綴相同且尚未被認領的實體檔案
        target_suffix = f"_{item['safe_word']}.mp3"
        for f in existing_files:
            if f.endswith(target_suffix) and f not in claimed_physical_files:
                old_path = os.path.join(OUTPUT_DIR, f)
                try:
                    os.rename(old_path, item["filepath"])
                    print(f"🔄 偵測到序號變更，已重新命名本機音檔：{f} -> {item['filename']} (免下載)")
                    claimed_physical_files.add(item["filename"])
                    renamed_count += 1
                    break
                except Exception as e:
                    print(f"⚠️ 重新命名失敗 {f}: {e}")
                    
    if renamed_count > 0:
        print(f"✨ 重命名優化完成！共快速移位了 {renamed_count} 個本機音檔。")

    # 3. 建立並行非同步下載任務，只下載真正缺失的音檔
    semaphore = asyncio.Semaphore(5)
    tasks = []
    for item in parsed_items:
        task = process_item(item, semaphore)
        tasks.append(task)

    print(f"開始處理 {len(tasks)} 筆資料，模式: {AUDIO_MODE} ...")
    await asyncio.gather(*tasks)
    print(f"\n✅ 下載與同步完成！")

    # 4. 清理未在預期清單中的舊垃圾/錯序號檔案
    expected_filenames = {item["filename"] for item in parsed_items}
    cleaned_count = 0
    for existing_file in os.listdir(OUTPUT_DIR):
        if existing_file.lower().endswith('.mp3'):
            if existing_file not in expected_filenames:
                garbage_path = os.path.join(OUTPUT_DIR, existing_file)
                try:
                    os.remove(garbage_path)
                    cleaned_count += 1
                except Exception as e:
                    print(f"⚠️ 無法刪除垃圾檔案 {existing_file}: {e}")
                    
    if cleaned_count > 0:
        print(f"🧹 已自動清理 {cleaned_count} 個舊的/順序對不上的垃圾音檔！")
        
    print(f"🎉 全部完成！檔案已完美儲存於 {OUTPUT_DIR} 資料夾。")

if __name__ == "__main__":
    asyncio.run(main())