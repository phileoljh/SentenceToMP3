import asyncio
import os
import re
import getpass
from openai import AsyncOpenAI

# =================設定區=================
INPUT_FILE = "mp3.md"            # 輸入的 Markdown 檔案
OUTPUT_DIR = "MP3_Output_OpenAI" # 輸出的資料夾名稱 (區分開原本的資料夾)

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

async def get_audio_bytes(client, text, voice):
    """呼叫 OpenAI API 生成語音並回傳二進位資料"""
    try:
        response = await client.audio.speech.create(
            model=MODEL_NAME,
            voice=voice,
            input=text
        )
        return response.content
    except Exception as e:
        print(f"   ⚠️ 語音生成錯誤 [{text}]: {e}")
        return b""


def clean_text_for_tts(text):
    """
    清洗送交 TTS 的文字，防止標點符號組合成表情符號導致誤讀。
    """
    if not text:
        return ""
    
    # 使用正規表達式在連續的標點符號中間插入空格
    cleaned = re.sub(r'([^\w\s])(?=[^\w\s])', r'\1 ', text)
    
    # 針對一些字母組成的常見表情符號（如 XD）也進行分隔
    cleaned = re.sub(r'([X])(?=[D])', r'\1 ', cleaned, flags=re.IGNORECASE)
    
    return cleaned

async def process_line(index, line, client, semaphore):
    """處理單一行 Markdown 表格資料"""
    async with semaphore:
        # 1. 預處理：去除前後空白
        line = line.strip()
        
        # 2. 過濾無效行
        if not line.startswith("|"): return
        if "English" in line and "中文" in line: return
        if "---" in line: return

        # 3. 解析表格欄位
        parts = [p.strip() for p in line.split('|')]
        # 去除 split 產生的頭尾空元素
        if parts[0] == "": parts.pop(0)
        if parts and parts[-1] == "": parts.pop()

        # 4. 偵測與提取資料 (自動相容 4 或 5 欄位)
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
            return

        # 5. 清理單字
        en_word = re.sub(r'^\d+\.\s*', '', raw_word_col)

        if not en_word: return

        # 6. 決定檔名
        safe_filename_text = re.sub(r'[\\/*?:"<>|]', "", en_word)
        filename = f"{index:04d}_{safe_filename_text}.mp3"
        filepath = os.path.join(OUTPUT_DIR, filename)

        # 檢查是否已存在 (跳過邏輯)
        if os.path.exists(filepath):
            print(f"⏩ 跳過已存在 [{index:04d}]: {en_word}")
            return

        print(f"處理中 [{index:04d}]: {en_word}")

        # 7. 依據模式生成語音片段
        audio_segments = []
        
        # 片段 A: 單字
        seg_a = await get_audio_bytes(client, clean_text_for_tts(en_word), VOICE_EN_WORD)
        if seg_a: audio_segments.append(seg_a)
        
        # 片段 B: 中文釋義
        if zh_def:
            seg_b = await get_audio_bytes(client, clean_text_for_tts(zh_def), VOICE_ZH)
            if seg_b: audio_segments.append(seg_b)

        # 片段 C: 英文例句
        if AUDIO_MODE == 2 and en_sentence:
            seg_c = await get_audio_bytes(client, clean_text_for_tts(en_sentence), VOICE_EN_SENT)
            if seg_c: audio_segments.append(seg_c)

        # 8. 寫入檔案
        if audio_segments:
            try:
                with open(filepath, "wb") as out_f:
                    for segment in audio_segments:
                        out_f.write(segment)
            except Exception as e:
                print(f"❌ 寫入失敗: {e}")

async def main():
    # 0. 輸入 API Key
    print("="*40)
    api_key = getpass.getpass("🔑 請輸入您的 OpenAI API Key (輸入時不會顯示): ")
    if not api_key:
        api_key = input("   (或是直接在此輸入): ") # 作為備用，有些環境 getpass 可能有問題
    
    if not api_key:
        print("❌ 未輸入 API Key，程式結束。")
        return
    print("="*40)

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

    # 初始化 OpenAI Client (使用 context manager 確保關閉)
    async with AsyncOpenAI(api_key=api_key) as client:
        # 限制並發數 (OpenAI 有 Rate Limit，建議不要設太高)
        semaphore = asyncio.Semaphore(3)
        tasks = []
        
        valid_count = 0
        for line in lines:
            if not line.strip().startswith("|"): continue
            # 過濾表頭關鍵字
            header_keywords = ["English", "(序號)", "序號", "英文片語", "---"]
            if any(kw in line for kw in header_keywords): continue
            
            valid_count += 1
            task = process_line(valid_count, line, client, semaphore)
            tasks.append(task)

        if tasks:
            print(f"開始處理 {len(tasks)} 筆資料 (OpenAI Mode) ...")
            await asyncio.gather(*tasks)
            print(f"\n✅ 全部完成！檔案已儲存於 {OUTPUT_DIR} 資料夾。")
        else:
            print("沒有偵測到有效的表格資料。")

if __name__ == "__main__":
    # Windows 平台 asyncio bug 修正
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n使用者中斷執行。")
