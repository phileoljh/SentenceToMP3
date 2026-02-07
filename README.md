# SentenceToMP3 單字語音生成與播放器製作工具

這個專案是一個自動化工具，旨在幫助語言學習者將整理好的單字與例句 (Markdown 表格格式) 轉換為語音 MP3 檔案，並自動生成一個互動式的網頁播放器 (`.html`)，方便進行聽力練習。

## ✨ 主要功能

1.  **文字轉語音**: 讀取 Markdown 中的單字、中文釋義及例句，使用微軟 Edge TTS (高品質 AI 語音) 生成 MP3。
2.  **自動生成播放器**: 將生成的 MP3 檔案整合為一個 HTML 網頁播放器，支援播放/暫停、上下首切換、自動連播及調整間隔時間。
3.  **多種模式**: 支援「僅單字+中文」或「單字+中文+例句」的朗讀模式。

## 🛠️ 環境需求

在執行此程式之前，請確保您的電腦已安裝以下軟體：

*   **Python 3.x**: 用於執行核心程式。
*   **PowerShell**: 用於執行自動化腳本 (Windows 內建)。
*   **Python 套件**:
    請使用 cmd 或 terminal 安裝必要的套件：
    ```bash
    pip install edge-tts
    ```

## 🚀 如何使用

### 1. 準備資料
請在專案根目錄下建立或編輯 `mp3.md` 檔案。內容必須為 Markdown 表格格式，格式如下：

```markdown
| 序號. 單字 | 中文解釋 | 英文例句 | 例句中譯 |
|---|---|---|---|
| 1. apple | 蘋果 | I eat an apple. | 我吃了一顆蘋果。 |
| 2. book | 書本 | This is a book. | 這是一本書。 |
```

> **注意**:
> * 第一欄必須包含序號 (如 `1. `, `2. `)，程式會自動去除。
> * 文件中可以包含 `---` 分隔線或 `English` 表頭，程式會自動過濾。

### 2. 執行程式
最簡單的方式是直接執行自動化腳本：

1.  找到 **`auto_generateMP3.ps1`** 檔案。
2.  按右鍵選擇「使用 PowerShell 執行」。

這個腳本會依序執行：
1.  `vocab_audio_md.py`: 生成 MP3 音檔 (存放在 `MP3_Output` 資料夾)。
2.  `create_player_mdV6fixed.py`: 生成網頁播放器 (`player_v6_fixed.html`)。

### 3. 開始學習
執行完成後，請打開生成的 **`player_v6_fixed.html`**，您就可以在瀏覽器中看到單字列表並開始聽力訓練了！

## 📂 檔案結構說明

*   **`auto_generateMP3.ps1`**: 主控制腳本，一鍵執行所有步驟。
*   **(New) `vocab_audio_openai.py`**: 使用 OpenAI TTS API 生成語音。
    *   **優點**: 提供更自然的真人發音模型 (`tts-1` / `tts-1-hd`)。
    *   **注意**: 執行時需輸入 OpenAI API Key，且會產生費用。
    *   具備「跳過已存在檔案」功能，節省 API 費用。
*   **`vocab_audio_md.py`**: 使用微軟 Edge TTS (免費) 生成語音。核心程式。
    *   可編輯程式碼中的 `AUDIO_MODE` 來切換是否朗讀例句。
    *   **更新**: 已加入「跳過已存在 MP3」檢查，若檔案已存在則不會重新生成。
*   **`create_player_mdV6fixed.py`**: 負責讀取產生的 MP3 與文字資料，生成 HTML 播放器介面。
*   **`mp3.md`**: (使用者提供) 您的單字筆記來源檔。
*   **`MP3_Output/`**: 存放使用 Edge TTS 生成的 MP3 檔案。
*   **`MP3_Output_OpenAI/`**: 存放使用 OpenAI TTS 生成的 MP3 檔案。
*   **`player_v6_fixed.html`**: 最終產出的網頁播放器。

## 🚀 如何使用 (OpenAI TTS 版本)

1.  確保已安裝 `openai` 套件：
    ```bash
    pip install openai
    ```
2.  執行程式：
    ```bash
    python vocab_audio_openai.py
    ```
3.  依照提示輸入 API Key。程式會自動生成 MP3 至 `MP3_Output_OpenAI` 資料夾。

## ⚙️ 進階設定 (修改程式碼)

如果您懂 Python，可以打開 `vocab_audio_md.py` 修改以下變數：

*   `AUDIO_MODE`:
    *   `1`: 僅朗讀「單字 + 中文」。
    *   `2`: 朗讀「單字 + 中文 + 英文例句」 (預設)。
*   `VOICE_EN_WORD` / `VOICE_ZH`: 修改朗讀的聲音角色 (如更換男女聲)。
