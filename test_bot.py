"""
ทดสอบ Bot โดยไม่ต้องใช้ LINE
รัน: python test_bot.py
"""

import os
import anthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ─── โหลด Knowledge Base ─────────────────────────────────────────────────────
def load_knowledge_base() -> str:
    with open("knowledge_base.md", "r", encoding="utf-8") as f:
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

# ─── ถามตอบ ───────────────────────────────────────────────────────────────────
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
history = []
MAX_HISTORY = 10

def ask_bot(question: str) -> str:
    history.append({"role": "user", "content": question})

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=history,
    )
    reply = response.content[0].text
    history.append({"role": "assistant", "content": reply})

    # จำกัดประวัติไม่เกิน MAX_HISTORY รอบ
    if len(history) > MAX_HISTORY * 2:
        del history[:2]

    return reply

# ─── Main Loop ────────────────────────────────────────────────────────────────
print("=" * 50)
print("🤖 ทดสอบ Bot โรงพยาบาลธีรพร")
print("พิมพ์คำถาม แล้วกด Enter | พิมพ์ 'ออก' เพื่อหยุด")
print("=" * 50)

while True:
    question = input("\n👤 คุณ: ").strip()
    if question.lower() in ["ออก", "exit", "quit"]:
        print("ปิดโปรแกรม")
        break
    if not question:
        continue
    print("\n🤖 Bot: ", end="", flush=True)
    answer = ask_bot(question)
    print(answer)
