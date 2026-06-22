# วิธีเชื่อมต่อ Facebook Page กับ Bot

## ภาพรวม

```
ลูกค้า Messenger / Comment
        ↓
Facebook Page
        ↓
Facebook Graph API → Webhook POST → Railway (skinchatbot)
        ↓
Claude AI → ตอบกลับอัตโนมัติ
```

---

## ขั้นตอนที่ 1 — สร้าง Meta Developer App

1. ไปที่ https://developers.facebook.com
2. คลิก **My Apps** → **Create App**
3. เลือก **Other** → **Next**
4. เลือก **Business** → **Next**
5. ใส่ชื่อ App เช่น `TheeraphornBot` → **Create App**

---

## ขั้นตอนที่ 2 — เพิ่ม Messenger Product

1. ใน Dashboard คลิก **Add Product**
2. หา **Messenger** → คลิก **Set up**
3. เลื่อนลงหา **Access Tokens**
4. คลิก **Add or Remove Pages** → เลือก Facebook Page ของโรงพยาบาล
5. Copy **Page Access Token** ไว้ (จะใช้ใน Railway)

---

## ขั้นตอนที่ 3 — ตั้งค่า Webhook

1. ใน Messenger settings เลื่อนหา **Webhooks**
2. คลิก **Add Callback URL**
3. ใส่:
   - **Callback URL:** `https://skinchatbot-production.up.railway.app/facebook/webhook`
   - **Verify Token:** `trpbeauty_verify_2024`
4. คลิก **Verify and Save**
5. หลัง verify สำเร็จ คลิก **Add Subscriptions** เลือก:
   - ✅ `messages`
   - ✅ `messaging_postbacks`
   - ✅ `feed` (สำหรับ Comment auto-reply)

---

## ขั้นตอนที่ 4 — เพิ่ม Environment Variables บน Railway

ไปที่ Railway → skinchatbot project → **Variables** แล้วเพิ่ม:

| Key | Value |
|-----|-------|
| `FB_PAGE_ACCESS_TOKEN` | Token จากขั้นตอนที่ 2 |
| `FB_APP_SECRET` | ดูได้ที่ App Settings → Basic → App Secret |
| `FB_VERIFY_TOKEN` | `trpbeauty_verify_2024` |

---

## ขั้นตอนที่ 5 — Subscribe Page to Webhook

ต้องทำผ่าน Graph API Explorer หรือ curl:

```bash
curl -X POST "https://graph.facebook.com/v19.0/{PAGE_ID}/subscribed_apps" \
  -d "subscribed_fields=messages,feed" \
  -d "access_token={PAGE_ACCESS_TOKEN}"
```

แทน `{PAGE_ID}` และ `{PAGE_ACCESS_TOKEN}` ด้วยค่าจริง

---

## ขั้นตอนที่ 6 — Deploy

```bash
git add -A
git commit -m "feat: add Facebook Messenger + Comment auto-reply"
git push origin main
```

Railway จะ deploy อัตโนมัติ

---

## ทดสอบ

- **Messenger:** ส่งข้อความหา Facebook Page → bot ตอบอัตโนมัติ
- **Comment:** Comment บน post ของ Page → bot ตอบใน comment

---

## คำสั่ง Admin (ใช้ได้กับทั้ง LINE และ Facebook)

- Bot ปิด/เปิดผ่าน LINE ตามเดิม (ใช้ `หยุดบอท` / `เปิดบอท`)
- Facebook webhook จะหยุดตอบอัตโนมัติเมื่อ bot ถูกปิด

---

## หมายเหตุสำคัญ

- App ต้องอยู่ใน **Live mode** (ไม่ใช่ Development) จึงจะรับข้อความจากคนอื่นได้
- ถ้ายังอยู่ใน Development mode จะตอบได้แค่ผู้ทดสอบที่ approved แล้ว
- Meta อาจต้อง review App ก่อน live หากขอ permission ระดับสูง (ปกติ `pages_messaging` ไม่ต้อง review)
