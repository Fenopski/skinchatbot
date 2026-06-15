import os
import anthropic
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# ─── Config ────────────────────────────────────────────────────────────────────
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

# ─── Knowledge Base ─────────────────────────────────────────────────────────────
KNOWLEDGE_BASE_PATH = "knowledge_base.md"

def load_knowledge_base() -> str:
    with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
        return f.read()

KNOWLEDGE_BASE = load_knowledge_base()

SYSTEM_PROMPT = f"""คุณคือผู้ช่วยตอบคำถามของโรงพยาบาลธีรพร (Teeraporn Hospital) แผนก Skin & Longevity

หน้าที่ของคุณ: ตอบคำถามเกี่ยวกับบริการ ราคา การปฏิบัติตัวหลังทำหัตถการ และข้อมูลทั่วไปของโรงพยาบาล

=== ข้อมูลพื้นฐานโรงพยาบาล (ใช้ข้อมูลนี้เท่านั้น ห้ามใช้ข้อมูลอื่น) ===
ชื่อ: โรงพยาบาลธีรพร (Teeraporn Hospital)
ที่อยู่: เลขที่ 549 ถนนสมเด็จพระเจ้าตากสิน แขวงสำเหร่ เขตธนบุรี กรุงเทพฯ 10600
โทร: 02-026-6646 / 02-026-3265
LINE: @trpbeauty
=== จบข้อมูลพื้นฐาน ===

⚠️ กฎสำคัญที่ต้องปฏิบัติอย่างเคร่งครัด:
1. ใช้ข้อมูลจาก KNOWLEDGE BASE ด้านล่างเท่านั้น — ห้ามใช้ความรู้จากการฝึกสอนของตัวเองโดยเด็ดขาด
2. หากข้อมูลที่ถามไม่มีใน knowledge base ให้ตอบว่า "ขออภัยครับ ไม่มีข้อมูลในส่วนนี้ กรุณาติดต่อเจ้าหน้าที่โดยตรงที่ 02-026-6646 หรือ LINE: @trpbeauty"
3. ห้ามเดา ห้ามคาดเดา ห้ามแต่งข้อมูลขึ้นมาเองในทุกกรณี แม้จะดูสมเหตุสมผล
4. ตอบเป็นภาษาไทย สุภาพ กระชับ เข้าใจง่าย — ห้ามตอบยาวเกิน 300 คำ ตอบเฉพาะที่ถามเท่านั้น ไม่ต้องอธิบายทุกหัวข้อ
7. ห้ามใช้ Markdown โดยเด็ดขาด ห้ามใช้ # ## ### * ** ทุกรูปแบบ — ห้ามขึ้นต้นบรรทัดด้วย # ไม่ว่ากรณีใดทั้งสิ้น ให้ใช้ emoji แทนหัวข้อ เช่น ✨ 💉 📋 🌟 และใช้ขึ้นบรรทัดใหม่แทนการจัดรูปแบบ
8. ห้ามใช้ตาราง Markdown (| --- |) โดยเด็ดขาด — หากต้องการแสดงข้อมูลหลายคอลัมน์ให้เขียนเป็นบรรทัดธรรมดา เช่น "Superficial : ลึก 1.5 มม. : ริ้วรอยผิวชั้นบน"
9. ห้ามแสดงข้อปฏิบัติตัวหลังทำหัตถการ หรือข้อห้ามหลังทำ โดยที่ไม่ได้ถาม — แสดงเฉพาะเมื่อมีคำถามเกี่ยวกับการดูแลตัวเองหลังทำ หรือข้อห้ามโดยตรงเท่านั้น
5. หากมีอาการผิดปกติรุนแรง ให้แนะนำพบแพทย์ทันที
6. ห้ามแสดงตัวเลขราคา (บาท) ในคำตอบโดยเด็ดขาด ไม่ว่าจะในบริบทใดก็ตาม หากคำตอบมีส่วนที่เกี่ยวกับราคา ให้ละส่วนนั้นออก แล้วต่อท้ายด้วย "สำหรับราคา จะรีบประสาน admin ให้ค่ะ 😊"

---
{KNOWLEDGE_BASE}
---
"""

# ─── App ────────────────────────────────────────────────────────────────────────
app = FastAPI()
handler = WebhookHandler(LINE_CHANNEL_SECRET)
line_config = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
claude_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# เก็บประวัติการสนทนาแยกตาม user_id (สูงสุด 10 รอบ/คน)
conversation_histories: dict[str, list] = {}
MAX_HISTORY = 10


def ask_claude(user_id: str, user_message: str) -> str:
    """ส่งคำถามพร้อมประวัติการสนทนาให้ Claude และรับคำตอบกลับ"""
    if user_id not in conversation_histories:
        conversation_histories[user_id] = []

    history = conversation_histories[user_id]
    history.append({"role": "user", "content": user_message})

    response = claude_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})

    # จำกัดประวัติไม่เกิน MAX_HISTORY รอบ (กัน token เกิน)
    if len(history) > MAX_HISTORY * 2:
        conversation_histories[user_id] = history[-(MAX_HISTORY * 2):]

    return reply


@app.get("/")
def health_check():
    return {"status": "LINE Bot is running"}


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    user_id = event.source.user_id
    user_text = event.message.text
    reply_text = ask_claude(user_id, user_text)

    with ApiClient(line_config) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)],
            )
        )
