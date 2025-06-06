import os
import random
import datetime
import pytz
import requests
from linebot import LineBotApi
from linebot.models import TextSendMessage, QuickReply, QuickReplyButton, MessageAction
import json
import time
import logging
import warnings

# --- 配置日誌 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# --- 環境變數與初始化 ---
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# 從 GitHub Actions 讀取今天是什麼節日
EVENT_NAME = os.getenv("EVENT_NAME", "一個神秘的特別日子")

if not LINE_CHANNEL_ACCESS_TOKEN or not GEMINI_API_KEY:
    logger.critical("缺少必要的環境變數 LINE_CHANNEL_ACCESS_TOKEN 或 GEMINI_API_KEY。")
    exit(1)

try:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    logger.info("LineBotApi (Holiday) 初始化成功。")
except Exception as e:
    logger.critical(f"初始化 LineBotApi (Holiday) 失敗: {e}", exc_info=True)
    exit(1)

GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# --- Gemini Prompt 生成 ---
def generate_holiday_prompt(event_name):
    prompt = f"""
    你現在扮演一隻叫做「小雲」的賓士公貓，個性害羞、溫和有禮、充滿好奇心且非常愛吃。
    今天是個非常特別的日子：【{event_name}】！

    請你完全以小雲的口吻，生成一則充滿節日氣氛、溫馨又可愛的廣播訊息。
    
    **重要格式要求 (請嚴格遵守)：**
    你的回應必須是一個**單一的 JSON 物件**，包含以下兩個 key：
    1.  `"holiday_message"`: (字串) 包含節日廣播的**主要文字內容**，使用 `\\n` 分隔。這段文字應該包含：
        *   一個吸引人的節日標題。
        *   一段小雲對這個節日的害羞觀察或感想。
        *   一句溫暖的祝福。
    2.  `"holiday_quest"`: (JSON 物件) 包含一個與節日相關的互動任務，結構如下：
        ```json
        {{
          "task_prompt": "這是一句引導用戶參與節日任務的、簡短又可愛的句子。",
          "buttons": [
            {{ "label": "第一個按鈕上顯示的文字(含Emoji)", "text": "用戶點擊後實際發送的文字" }},
            {{ "label": "第二個按鈕上顯示的文字(含Emoji)", "text": "用戶點擊後實際發送的文字" }}
          ]
        }}
        ```

    ---
    **【風格靈感參考】(請勿直接抄襲，要根據傳入的 {event_name} 創造全新的內容！)**
    *   **如果今天是「聖誕節」:**
        - "holiday_message": "🎄叮叮噹～叮叮噹～🎄\\n咪...聽說今天是聖誕節...你家裡有那個亮晶晶、會發光的樹嗎？小雲好好奇喔...\\n希望你今天也能收到很多很多的溫暖和快樂！",
        - "holiday_quest": {{ "task_prompt": "🐾 聖誕小任務：", "buttons": [{{ "label": "🎁 交換禮物！", "text": "小雲，我們來交換禮物吧！" }}, {{ "label": "幫小雲戴聖誕帽", "text": "（偷偷幫小雲戴上聖誕帽）" }}] }}
    *   **如果今天是「貓之日」:**
        - "holiday_message": "🐾 Happy Cat Day! 🐾\\n喵嗚～聽說今天...是屬於我們貓貓的日子耶！>///<\\n那...今天你可以多摸摸我的頭嗎？就一下下就好...",
        - "holiday_quest": {{ "task_prompt": "🐾 貓之日特別任務：", "buttons": [{{ "label": "給小雲罐罐", "text": "（拿出一個頂級貓咪罐罐）" }}, {{ "label": "對小雲說你愛他", "text": "小雲，我最喜歡你了！" }}] }}
    *   **如果今天是「新年」:**
        - "holiday_message": "🎆 新年快樂！🎆\\n咻～砰！外面剛剛有好大、好亮的煙火...小雲嚇了一跳，但...真的好漂亮喔...\\n新的一年，也請你多多指教了喵...",
        - "holiday_quest": {{ "task_prompt": "🐾 新年新希望：", "buttons": [{{ "label": "告訴小雲你的新年新希望", "text": "我的新年新希望是..." }}, {{ "label": "跟小雲一起倒數", "text": "5...4...3...2...1...新年快樂！" }}] }}
    ---

    **現在，請為【{event_name}】這個節日，生成包含 "holiday_message" 和 "holiday_quest" 的 JSON 物件。**
    請確保內容高度原創、符合小雲的個性，且 JSON 格式完全正確。
    """
    return prompt

# --- 主邏輯 ---
def get_holiday_message_and_broadcast():
    logger.info(f"開始為節日【{EVENT_NAME}】生成廣播內容...")
    
    prompt = generate_holiday_prompt(EVENT_NAME)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.9, "maxOutputTokens": 2048, "response_mime_type": "application/json"}
    }

    try:
        response = requests.post(GEMINI_API_URL, headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}, json=payload, timeout=90)
        response.raise_for_status()
        
        result_json = response.json()
        logger.debug(f"Gemini (Holiday) API 原始回應: {json.dumps(result_json, ensure_ascii=False, indent=2)}")
        
        content_part = result_json["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content_part)

        holiday_message = data.get("holiday_message")
        quest_data = data.get("holiday_quest")

        if not holiday_message or not quest_data:
            raise ValueError("從 Gemini 返回的 JSON 缺少必要的鍵。")

        messages_to_send = [TextSendMessage(text=holiday_message)]
        
        task_prompt = quest_data.get("task_prompt")
        buttons_data = quest_data.get("buttons")

        if task_prompt and buttons_data:
            quick_reply_items = [
                QuickReplyButton(action=MessageAction(label=btn.get("label"), text=btn.get("text")))
                for btn in buttons_data
            ]
            messages_to_send.append(
                TextSendMessage(text=task_prompt, quick_reply=QuickReply(items=quick_reply_items))
            )

        logger.info(f"準備廣播 {len(messages_to_send)} 則節日訊息...")
        line_bot_api.broadcast(messages=messages_to_send)
        logger.info(f"節日【{EVENT_NAME}】的訊息已成功廣播！")

    except Exception as e:
        logger.critical(f"生成或廣播節日訊息時發生嚴重錯誤: {e}", exc_info=True)
        # 也可以在這裡加入一個備用的、發送失敗的通知給自己

if __name__ == "__main__":
    logger.info(f"========== 小雲節日廣播腳本開始執行 ==========")
    logger.info(f"偵測到節日事件: 【{EVENT_NAME}】")
    get_holiday_message_and_broadcast()
    logger.info(f"========== 小雲節日廣播腳本執行完畢 ==========")
