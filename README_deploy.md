# คู่มือ Deploy LINE Bot — Teeraporn Hospital

## ภาพรวม
```
ลูกค้าพิมพ์ใน LINE → LINE API → Webhook (Render.com) → Claude AI → ตอบกลับ
```

---

## ขั้นตอนที่ 1 — สมัคร LINE Messaging API (ฟรี)

1. ไปที่ https://developers.line.biz/console/
2. Login ด้วย LINE account
3. กด **Create a new provider** → ตั้งชื่อ (เช่น "Teeraporn Hospital")
4. กด **Create a new channel** → เลือก **Messaging API**
5. กรอกข้อมูล:
   - Channel name: ชื่อ Bot (เช่น "TRP Aftercare")
   - Channel description: "ผู้ช่วยตอบคำถามหลังทำหัตถการ"
   - Category: Healthcare
6. กด **Create**
7. ไปที่แท็บ **Messaging API** → จดค่าสองอย่างนี้:
   - **Channel Secret** (แท็บ Basic settings)
   - **Channel Access Token** → กด "Issue" เพื่อสร้าง

---

## ขั้นตอนที่ 2 — สมัคร Anthropic API

1. ไปที่ https://console.anthropic.com/
2. สมัครบัญชี → เติมเครดิต (เริ่มต้น $5 เพียงพอสำหรับทดสอบ)
3. ไปที่ **API Keys** → กด **Create Key**
4. จด **API Key** ไว้

---

## ขั้นตอนที่ 3 — Deploy บน Render.com (ฟรี)

### 3.1 อัพโหลดโค้ดขึ้น GitHub
1. สมัคร https://github.com (ถ้ายังไม่มี)
2. สร้าง Repository ใหม่ (ชื่ออะไรก็ได้ เช่น `trp-linebot`)
3. อัพโหลดไฟล์ทั้งหมดในโฟลเดอร์นี้:
   - `main.py`
   - `requirements.txt`
   - `knowledge_base.md`

### 3.2 Deploy บน Render
1. ไปที่ https://render.com → สมัคร/Login
2. กด **New** → **Web Service**
3. เชื่อม GitHub → เลือก repository ที่สร้างไว้
4. ตั้งค่า:
   - **Name**: trp-linebot
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. เลื่อนลงหา **Environment Variables** → กด **Add Environment Variable** ทีละตัว:

   | Key | Value |
   |-----|-------|
   | `LINE_CHANNEL_SECRET` | (จากขั้นตอนที่ 1) |
   | `LINE_CHANNEL_ACCESS_TOKEN` | (จากขั้นตอนที่ 1) |
   | `ANTHROPIC_API_KEY` | (จากขั้นตอนที่ 2) |

6. กด **Create Web Service**
7. รอ Deploy เสร็จ (~2-3 นาที) → จะได้ URL เช่น `https://trp-linebot.onrender.com`

---

## ขั้นตอนที่ 4 — เชื่อม Webhook กับ LINE

1. กลับไปที่ LINE Developer Console
2. แท็บ **Messaging API**
3. หา **Webhook URL** → ใส่: `https://trp-linebot.onrender.com/webhook`
4. กด **Verify** → ต้องขึ้น "Success"
5. เปิด **Use webhook** ให้เป็น ON
6. ปิด **Auto-reply messages** และ **Greeting messages** (ถ้าไม่ต้องการ)

---

## ขั้นตอนที่ 5 — ทดสอบ

1. แสกน QR Code ของ Bot ใน LINE Developer Console
2. Add Bot เป็นเพื่อน
3. พิมพ์คำถาม เช่น "หลังทำโบท็อกซ์ต้องระวังอะไรบ้าง?"
4. Bot ควรตอบกลับภายใน 5-10 วินาที

---

## หมายเหตุสำคัญ

- **Render Free Tier**: Server จะ sleep หลังไม่มีการใช้งาน 15 นาที → ครั้งแรกอาจช้า 30-60 วินาที
  - แก้ได้โดยอัพเกรดเป็น Render Paid ($7/เดือน) หรือใช้ Railway.app
- **ค่าใช้จ่าย Claude API**: ประมาณ $0.001 ต่อการสนทนา 1 ครั้ง (ถูกมาก)
- **LINE Free Tier**: รับส่งข้อความได้ 200 ครั้ง/เดือนฟรี (ถ้าเกินต้องเสียเงิน)

---

## ติดต่อขอความช่วยเหลือ

หากติด Deploy ขั้นตอนไหน บอก Claude ได้เลยครับ!
