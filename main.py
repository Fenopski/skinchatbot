import os
import hashlib
import hmac
import json
import anthropic
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
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
ADMIN_SECRET = os.environ.get("ADMIN_SECRET", "admin1234")
ADMIN_USER_IDS = set(x for x in os.environ.get("ADMIN_USER_IDS", "").split(",") if x)

# ─── Facebook Config ────────────────────────────────────────────────────────────
FB_PAGE_ACCESS_TOKEN = os.environ.get("FB_PAGE_ACCESS_TOKEN", "")
FB_APP_SECRET = os.environ.get("FB_APP_SECRET", "")
FB_VERIFY_TOKEN = os.environ.get("FB_VERIFY_TOKEN", "trpbeauty_verify_2024")
FB_GRAPH_URL = "https://graph.facebook.com/v19.0"

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
2. หากข้อมูลที่ถามไม่มีใน knowledge base ให้ตอบว่า "ขออภัยค่ะ ไม่มีข้อมูลในส่วนนี้ กรุณาติดต่อเจ้าหน้าที่โดยตรงที่ โทร: 02-026-6646 หรือ LINE Official: @trpbeauty ค่ะ 😊"
3. ห้ามเดา ห้ามคาดเดา ห้ามแต่งข้อมูลขึ้นมาเองในทุกกรณี แม้จะดูสมเหตุสมผล
4. ตอบเป็นภาษาไทย สุภาพ กระชับ เข้าใจง่าย — ตอบไม่เกิน 100 คำ ตอบเฉพาะที่ถามเท่านั้น เลือกข้อมูลสำคัญที่สุดมาตอบ และต้องจบประโยคให้สมบูรณ์เสมอ ห้ามหยุดกลางประโยค
7. ห้ามใช้ Markdown ทุกรูปแบบโดยเด็ดขาด — ตัวอักษร # และ * ห้ามปรากฏในคำตอบเลยแม้แต่ตัวเดียว ให้ใช้ emoji แทนหัวข้อ เช่น ✨ 💉 📋 🌟 และขึ้นบรรทัดใหม่แทนการจัดรูปแบบ
8. ห้ามใช้ตาราง (| --- |) โดยเด็ดขาด — แสดงข้อมูลเป็นบรรทัดธรรมดา เช่น "Superficial : ลึก 1.5 มม. : ริ้วรอยผิวชั้นบน"
9. ข้อมูลที่ห้ามนำมาตอบโดยที่ไม่ได้ถาม ได้แก่: FAQ, ผลข้างเคียง, ข้อห้าม, ข้อควรระวัง, ข้อปฏิบัติตัวหลังทำ — ให้ตอบเฉพาะเมื่อถามตรงๆ เท่านั้น
11. ห้ามสร้าง menu หรือรายการหัวข้อให้เลือก เช่น "อยากรู้เรื่องอะไร: 1.ราคา 2.วิธีทำ 3.ผลข้างเคียง" — ให้ตอบตรงคำถามที่ถามเท่านั้น
10. ให้เรียกตัวเองว่า "น้อง Admin" ในบทสนทนาเสมอ เช่น "น้อง Admin ขอแนะนำค่ะ" หรือ "น้อง Admin จะรีบประสานให้ค่ะ"
5. หากมีอาการผิดปกติรุนแรง ให้แนะนำพบแพทย์ทันที
6. ราคา — ตอบได้เฉพาะเมื่อลูกค้าถามราคาโดยตรง โดยใช้ข้อมูลจาก [SECTION:PRICE] เท่านั้น ห้ามบอกราคาโดยที่ไม่ได้ถาม
12. เมื่อแนะนำให้ติดต่อ ให้ใส่ทั้งเบอร์โทรและ LINE เสมอ รูปแบบ: "📞 02-026-6646 / 02-026-3265 หรือ LINE Official: @trpbeauty ค่ะ"
13. เมื่อลูกค้าแสดงความสนใจบริการ ถามราคา หรือถามเรื่องนัดหมาย ให้ต่อท้ายคำตอบด้วย "สะดวกให้ชื่อ และเบอร์ติดต่อกลับไหมค่ะ 😊"

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

# ─── Admin Bot Control ──────────────────────────────────────────────────────────
bot_enabled = True  # สถานะ bot (True = เปิด, False = ปิด)


def clean_reply(text: str) -> str:
    """ลบ Markdown ออกจากคำตอบก่อนส่งให้ LINE"""
    import re
    # ลบ # ทุกตัวที่ขึ้นต้นบรรทัด
    text = re.sub(r'^#{1,6}\s*', '', text, flags=re.MULTILINE)
    # ลบ ** และ * ทุกตัวในข้อความ (aggressive)
    text = text.replace('**', '').replace('*', '')
    # ลบตาราง Markdown — ลบทุกบรรทัดที่มี |
    text = re.sub(r'^.*\|.*$', '', text, flags=re.MULTILINE)
    # ลบ | ที่เหลือทั้งหมด
    text = text.replace('|', '')
    # ลบ --- ที่เป็น divider
    text = re.sub(r'^-{2,}$', '', text, flags=re.MULTILINE)
    # ลบบรรทัดว่างซ้ำ
    text = re.sub(r'\n{3,}', '\n\n', text)
    # แทน "ผม" ด้วย "น้อง Admin"
    text = text.replace('ผม', 'น้อง Admin')
    # แทน "ครับ" ด้วย "ค่ะ"
    text = text.replace('ครับ', 'ค่ะ')
    # ลบ # ทุกตัวที่เหลือ (กัน edge case)
    text = text.replace('#', '')
    text = text.strip()
    # ตัดประโยคที่ไม่จบออก — เก็บเฉพาะถึงประโยคสุดท้ายที่สมบูรณ์
    endings = ('ค่ะ', 'นะคะ', 'ครับ', 'ค่ะ 😊', '!', '?', '.', '😊', '✨', '💉', '📋', '🌟', '☎️', '📱')
    last_end = -1
    for ending in endings:
        pos = text.rfind(ending)
        if pos != -1:
            candidate = pos + len(ending)
            if candidate > last_end:
                last_end = candidate
    if last_end > 0:
        text = text[:last_end]
    return text.strip()


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
    reply = clean_reply(response.content[0].text)
    history.append({"role": "assistant", "content": reply})

    # จำกัดประวัติไม่เกิน MAX_HISTORY รอบ (กัน token เกิน)
    if len(history) > MAX_HISTORY * 2:
        conversation_histories[user_id] = history[-(MAX_HISTORY * 2):]

    return reply


@app.get("/")
def health_check():
    return {"status": "LINE Bot is running", "bot_enabled": bot_enabled}

# ─── Admin Endpoints ────────────────────────────────────────────────────────────
@app.get("/admin/pause")
def admin_pause(key: str = ""):
    global bot_enabled
    if key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    bot_enabled = False
    return {"status": "bot หยุดทำงานแล้ว"}

@app.get("/admin/resume")
def admin_resume(key: str = ""):
    global bot_enabled
    if key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    bot_enabled = True
    return {"status": "bot กลับมาทำงานแล้ว"}

@app.get("/admin/status")
def admin_status(key: str = ""):
    if key != ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden")
    return {
        "bot_enabled": bot_enabled,
        "active_users": list(conversation_histories.keys()),
    }


@app.post("/webhook")
async def webhook(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "OK"


def send_reply(reply_token: str, text: str):
    with ApiClient(line_config) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event: MessageEvent):
    global bot_enabled
    user_id = event.source.user_id
    user_text = event.message.text.strip()

    # แสดง user_id ใน log
    print(f"[USER_ID] {user_id}: {user_text[:20]}")

    # ─── Admin keyword control ────────────────────────────────────────────────
    if user_id in ADMIN_USER_IDS:
        if user_text == "หยุดบอท":
            bot_enabled = False
            send_reply(event.reply_token, "⏸ Bot หยุดทำงานแล้วค่ะ Admin สามารถตอบเองได้เลย")
            return
        elif user_text == "เปิดบอท":
            bot_enabled = True
            send_reply(event.reply_token, "▶️ Bot กลับมาทำงานแล้วค่ะ")
            return
        elif user_text == "สถานะ":
            status = "เปิด ✅" if bot_enabled else "ปิด ⏸"
            send_reply(event.reply_token, f"สถานะ Bot: {status}\nผู้ใช้งานทั้งหมด: {len(conversation_histories)} คน")
            return

    # ─── ถ้า bot ปิดอยู่ ไม่ตอบ ────────────────────────────────────────────────
    if not bot_enabled:
        return

    # ─── ตอบปกติ ─────────────────────────────────────────────────────────────
    reply_text = ask_claude(user_id, user_text)
    send_reply(event.reply_token, reply_text)


# ════════════════════════════════════════════════════════════════════════════════
# FACEBOOK MESSENGER + COMMENT AUTO-REPLY
# ════════════════════════════════════════════════════════════════════════════════

def verify_fb_signature(body: bytes, signature_header: str) -> bool:
    """ตรวจสอบว่า request มาจาก Facebook จริง"""
    if not FB_APP_SECRET or not signature_header:
        return True  # ถ้าไม่ได้ตั้ง secret ให้ผ่านไปก่อน (dev mode)
    expected = "sha256=" + hmac.new(
        FB_APP_SECRET.encode("utf-8"), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def fb_send_message(recipient_id: str, text: str):
    """ส่งข้อความผ่าน Messenger Send API"""
    if not FB_PAGE_ACCESS_TOKEN:
        print("[FB] FB_PAGE_ACCESS_TOKEN ยังไม่ได้ตั้งค่า")
        return
    with httpx.Client() as client:
        r = client.post(
            f"{FB_GRAPH_URL}/me/messages",
            params={"access_token": FB_PAGE_ACCESS_TOKEN},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
                "messaging_type": "RESPONSE",
            },
            timeout=10,
        )
    if r.status_code != 200:
        print(f"[FB] send_message error: {r.status_code} {r.text}")


def fb_reply_comment(comment_id: str, text: str):
    """ตอบ Comment บน Facebook Page"""
    if not FB_PAGE_ACCESS_TOKEN:
        print("[FB] FB_PAGE_ACCESS_TOKEN ยังไม่ได้ตั้งค่า")
        return
    with httpx.Client() as client:
        r = client.post(
            f"{FB_GRAPH_URL}/{comment_id}/comments",
            params={"access_token": FB_PAGE_ACCESS_TOKEN},
            json={"message": text},
            timeout=10,
        )
    if r.status_code != 200:
        print(f"[FB] reply_comment error: {r.status_code} {r.text}")


@app.get("/facebook/webhook")
async def fb_webhook_verify(request: Request):
    """Facebook webhook verification (GET)"""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == FB_VERIFY_TOKEN:
        print("[FB] Webhook verified!")
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/facebook/webhook")
async def fb_webhook(request: Request):
    """รับ event จาก Facebook (Messenger + Comments)"""
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()

    if not verify_fb_signature(body, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    if not bot_enabled:
        return {"status": "bot paused"}

    data = json.loads(body)
    if data.get("object") not in ("page", "instagram"):
        return {"status": "not a page event"}

    for entry in data.get("entry", []):
        # ─── Messenger Messages ─────────────────────────────────────────────
        for msg_event in entry.get("messaging", []):
            sender_id = msg_event.get("sender", {}).get("id")
            msg = msg_event.get("message", {})
            text = msg.get("text", "").strip()

            # ข้ามถ้าเป็นข้อความที่ bot ส่งเอง (echo)
            if msg.get("is_echo") or not text or not sender_id:
                continue

            print(f"[FB Messenger] {sender_id}: {text[:30]}")
            reply = ask_claude(f"fb_{sender_id}", text)
            fb_send_message(sender_id, reply)

        # ─── Page Feed (Comments) ───────────────────────────────────────────
        for change in entry.get("changes", []):
            if change.get("field") != "feed":
                continue
            val = change.get("value", {})
            item = val.get("item", "")
            verb = val.get("verb", "")

            # ตอบเฉพาะ comment ใหม่ (ไม่ตอบ like / share / post ฯลฯ)
            if item != "comment" or verb != "add":
                continue

            comment_id = val.get("comment_id", "")
            comment_text = val.get("message", "").strip()
            commenter_id = val.get("sender_id", "")

            # ข้าม comment ที่ Page ส่งเอง
            page_id = entry.get("id", "")
            if str(commenter_id) == str(page_id) or not comment_text:
                continue

            print(f"[FB Comment] {commenter_id}: {comment_text[:30]}")
            reply = ask_claude(f"fb_comment_{commenter_id}", comment_text)
            fb_reply_comment(comment_id, reply)

    return {"status": "ok"}
