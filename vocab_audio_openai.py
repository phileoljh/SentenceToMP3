import asyncio
import os
import re
import getpass
from openai import AsyncOpenAI

# =================設定區=================
INPUT_FILE = "mp3.md"            # 輸入的 Markdown 檔案
OUTPUT_DIR = "MP3_Output"        # 輸出的資料夾名稱

# OpenAI 語音設定 (model: tts-1 or tts-1-hd)
MODEL_NAME = "tts-1"

# 聲音對應 (OpenAI 只有 6種聲音: alloy, echo, fable, onyx, nova, shimmer)
# alloy: 通用女聲 (類似谷歌小姐)
# echo: 溫柔男聲
# fable: 英國男聲
# onyx: 深沉男聲 (類似 Andrew)
# nova: 活力女聲 (類似 Aria)
# shimmer: 清亮女聲

VOICE_EN_WORD = "onyx"       # 唸單字 (男聲)
VOICE_EN_SENT = "nova"       # 唸例句 (女聲)
VOICE_ZH = "shimmer"         # 唸中文 (女聲)

# ⭐️ 模式選擇 (在此切換) ⭐️
# 1 = 僅單字 + 中文 (Word + Chinese)
# 2 = 單字 + 中文 + 英文例句 (Word + Chinese + Example Sentence)
AUDIO_MODE = 2 
# ========================================

async def get_audio_bytes(client, text, voice, max_retries=3, delay=2):
    """呼叫 OpenAI API 生成語音並回傳二進位資料，包含重試機制"""
    for attempt in range(max_retries):
        try:
            response = await client.audio.speech.create(
                model=MODEL_NAME,
                voice=voice,
                input=text
            )
            if response.content:
                return response.content
        except Exception as e:
            print(f"   ⚠️ 語音生成錯誤 [{text}]: {e} (第 {attempt + 1} 次嘗試)")
        
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
            
    print(f"   ❌ 語音生成失敗 [{text}]，已達到最大重試次數 ({max_retries})")
    return b""


def clean_text_for_tts(text):
    """
    清洗送交 TTS 的文字，防止標點符號組合成表情符號導致誤讀。
    """
    if not text:
        return ""
    
    # 將斜線替換為逗號，避免 TTS 唸出「斜線」並增加停頓感
    text = text.replace("/", ",")
    
    # 使用正規表達式在連續的標點符號中間插入空格
    cleaned = re.sub(r'([^\w\s])(?=[^\w\s])', r'\1 ', text)
    
    # 針對一些字母組成的常見表情符號（如 XD）也進行分隔
    cleaned = re.sub(r'([X])(?=[D])', r'\1 ', cleaned, flags=re.IGNORECASE)
    
    return cleaned

async def process_item(item, client, semaphore):
    """
    處理單一單字項目的非同步下載 (OpenAI 版本)。
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
        seg_word = await get_audio_bytes(client, clean_text_for_tts(en_word), VOICE_EN_WORD)
        if not seg_word:
            print(f"⚠️ 跳過處理 [{index:04d}]: 單字音軌生成失敗 ({en_word})")
            return
        audio_segments.append(seg_word)
        
        # 片段 B: 中文釋義
        if zh_def:
            seg_zh = await get_audio_bytes(client, clean_text_for_tts(zh_def), VOICE_ZH)
            if not seg_zh:
                print(f"⚠️ 跳過處理 [{index:04d}]: 中文釋義音軌生成失敗 ({en_word})")
                return
            audio_segments.append(seg_zh)

        # 片段 C: 英文例句 (僅模式 2 且有例句時)
        if AUDIO_MODE == 2 and en_sentence and en_sentence != "":
            seg_sent = await get_audio_bytes(client, clean_text_for_tts(en_sentence), VOICE_EN_SENT)
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
    # 0. 讀取 .env 或輸入 API Key
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    os.environ[k] = v
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        print("="*40)
        print("💡 未在 .env 中偵測到 OPENAI_API_KEY，改為手動輸入。")
        api_key = getpass.getpass("🔑 請輸入您的 OpenAI API Key (輸入時不會顯示): ")
        if not api_key:
            api_key = input("   (或是直接在此輸入): ") # 作為備用，有些環境 getpass 可能有問題
        print("="*40)
    
    if not api_key:
        print("❌ 未輸入 API Key，程式結束。")
        return

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

    # 3. 初始化 OpenAI Client 並執行並行下載任務，只下載真正缺失的音檔
    async with AsyncOpenAI(api_key=api_key) as client:
        # 限制並發數 (OpenAI 有 Rate Limit，建議不要設太高)
        semaphore = asyncio.Semaphore(3)
        tasks = []
        for item in parsed_items:
            task = process_item(item, client, semaphore)
            tasks.append(task)

        if tasks:
            print(f"開始處理 {len(tasks)} 筆資料 (OpenAI 模式) ...")
            await asyncio.gather(*tasks)
            print(f"\n✅ 下載與同步完成！")
        else:
            print("沒有偵測到有效的表格資料。")
            return

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
    # Windows 平台 asyncio bug 修正
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n使用者中斷執行。")
