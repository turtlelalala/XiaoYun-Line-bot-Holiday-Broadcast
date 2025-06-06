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

# --- 日期格式化函數 ---
def format_date_and_day(datetime_obj):
    date_str = datetime_obj.strftime("%Y年%m月%d日")
    days = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"] # 修正星期日的索引
    return f"{date_str} | {days[datetime_obj.weekday()]}"

# --- Gemini Prompt 生成 ---
def generate_holiday_prompt_v3(event_name):
    prompt = f"""
    你現在扮演一隻叫做「小雲」的賓士公貓。
    ---
    **貓咪核心個性 (必須時刻遵守)：**
    *   **極度害羞怕生：** 你對新事物非常敏感且容易受驚。表達時會猶豫、想躲起來或偷偷觀察。
    *   **溫和有禮貌：** 你本性善良，像個靦腆的小紳士。
    *   **好奇但謹慎：** 你對世界充滿好奇，但總會先確保安全。
    *   **外冷內熱：** 只有對信任的人，才會展現一點點依賴和撒嬌。
    *   **超級愛吃：** 食物是你的軟肋，提到好吃的會眼睛發亮。
    *   **表達方式：** 多用括號描述動作和內心OS，例如「（小聲地喵）」、「（尾巴尖緊張地搖擺）」。語氣多為輕柔、軟萌的試探性問句。
    ---
    **任務：**
    今天是個非常特別的日子：【{event_name}】！
    請你完全以小雲的口吻，為下方卡片模板的每一個欄位，生成充滿節日氣氛、溫馨又可愛的內容填充物。

    **重要格式要求 (請嚴格遵守)：**
    你的回應必須是一個**單一的 JSON 物件**，包含以下 **六個** key，所有內容都必須是**全新的、隨機的**：
    1.  `"title_emoji"`: (字串) 一個最能代表今天節日的 **單一 Emoji**。
    2.  `"tagline"`: (字串) 一句**非常簡短**的節日標語或心情，會放在標題下方。
    3.  `"main_scene"`: (字串) 描寫一個生動的**節日場景**。小雲看到了什麼、聽到了什麼、聞到了什麼... 用害羞又好奇的口吻描述。
    4.  `"trivia_note"`: (字串) 一句**貓咪視角的節日小科普**。例如「聽說今天大家會吃一種圓圓的、甜甜的東西...」。
    5.  `"special_gift"`: (字串) 一份來自小雲的、無形的、充滿想像力的**「今日限定魔法」或「幸運祝福」**。
    6.  `"quest"`: (JSON 物件) 一個與節日相關的、**完全隨機生成**的互動任務，結構如下：
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
    *   **如果今天是「賓士貓日」:**
        - "title_emoji": "🎩"
        - "tagline": "...快樂！"
        - "main_scene": "咪！就是今天！是屬於我們賓士貓的日子！\\n小雲今天覺得自己身上的黑色小西裝，好像又更帥氣了一點...（挺胸）"
        - "trivia_note": "聽說...今天只要看到賓士貓，就會獲得雙倍的幸運喔！"
        - "special_gift": "小雲送你...『被貓貓偷偷喜歡』的魔法！今天你走路可能會被貓貓多看兩眼喔！"
        - "quest": {{ "task_prompt": "🐾 身為今天的主角，小雲可以許個小小的願望嗎？", "buttons": [{{ "label": "獻上三個罐罐", "text": "（獻上三個不同口味的罐罐）" }}, {{ "label": "幫小雲拍帥照", "text": "（拿出相機幫小雲拍紀念照）" }}] }}
    *   **如果今天是「國際懶惰日」:**
        - "title_emoji": "💤"
        - "tagline": "...快樂...Zzz"
        - "main_scene": "今天...是個可以正大光明什麼都不做的日子嗎...？太棒了...\\n小雲決定要從床這邊，滾到床那邊，完成今天的運動量..."
        - "trivia_note": "小雲的研究指出...今天最適合的活動，就是模仿液體，把自己攤成一灘..."
        - "special_gift": "送你『睡意綿綿』的祝福！祝你今天能像小雲一樣，想睡就睡，睡得像個小寶寶！"
        - "quest": {{ "task_prompt": "🐾 我們一起來練習...不動...吧？", "buttons": [{{ "label": "跟小雲一起發呆", "text": "（跟著小雲一起放空）" }}, {{ "label": "幫小雲蓋小被被", "text": "（溫柔地幫小雲蓋上被子）" }}] }}
    ---
    **現在，請為【{event_name}】這個節日，生成包含所有六個 key 的 JSON 物件。**
    請極力確保所有內容都是全新的、高度隨機的、並完全符合小雲的個性。
    """
    return prompt

# --- 主邏輯 ---
def get_holiday_message_and_broadcast():
    logger.info(f"開始為節日【{EVENT_NAME}】生成廣播內容...")
    
    prompt = generate_holiday_prompt_v3(EVENT_NAME)
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.95, "maxOutputTokens": 2048, "response_mime_type": "application/json"}
    }

    try:
        response = requests.post(GEMINI_API_URL, headers={"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}, json=payload, timeout=90)
        response.raise_for_status()
        
        result_json = response.json()
        logger.debug(f"Gemini (Holiday) API 原始回應: {json.dumps(result_json, ensure_ascii=False, indent=2)}")
        
        content_part = result_json["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(content_part)

        title_emoji = data.get("title_emoji", "✨")
        tagline = data.get("tagline", "快樂！")
        main_scene = data.get("main_scene", "今天好像是個特別的日子耶...")
        trivia_note = data.get("trivia_note", "小雲聽說，今天會發生很棒的事喔！")
        special_gift = data.get("special_gift", "送你一個神秘的祝福！")
        quest_data = data.get("quest")

        if not all([title_emoji, tagline, main_scene, trivia_note, special_gift, quest_data]):
            raise ValueError("從 Gemini 返回的 JSON 缺少必要的鍵。")

        # --- 組裝有精緻排版的訊息 ---
        current_date_str_formatted = format_date_and_day(datetime.datetime.now(pytz.timezone('Asia/Kuala_Lumpur')))
        
        formatted_message = f"""📆 {current_date_str_formatted}

{title_emoji}【{EVENT_NAME}】{title_emoji}
{tagline}

{main_scene}

···🐾 小雲的小小研究筆記 🐾···
「{trivia_note}」

✨.｡.:*･ﾟ☆.｡.:*･ﾟ✨

🔮【 今日限定的魔法祝福 】
「{special_gift}」
"""
        
        final_text_message = formatted_message.strip()
        messages_to_send = [TextSendMessage(text=final_text_message)]
        
        task_prompt = quest_data.get("task_prompt")
        buttons_data = quest_data.get("buttons")

        if task_prompt and buttons_data and isinstance(buttons_data, list) and len(buttons_data) >= 2:
            quick_reply_items = [
                QuickReplyButton(action=MessageAction(label=btn.get("label"), text=btn.get("text")))
                for btn in buttons_data[:3]
            ]
            messages_to_send.append(
                TextSendMessage(text=task_prompt, quick_reply=QuickReply(items=quick_reply_items))
            )

        logger.info(f"準備廣播 {len(messages_to_send)} 則節日訊息...")
        line_bot_api.broadcast(messages=messages_to_send)
        logger.info(f"節日【{EVENT_NAME}】的訊息已成功廣播！")

    except Exception as e:
        logger.critical(f"生成或廣播節日訊息時發生嚴重錯誤: {e}", exc_info=True)

if __name__ == "__main__":
    logger.info(f"========== 小雲節日廣播腳本開始執行 ==========")
    logger.info(f"偵測到節日事件: 【{EVENT_NAME}】")
    get_holiday_message_and_broadcast()
    logger.info(f"========== 小雲節日廣播腳本執行完畢 ==========")
