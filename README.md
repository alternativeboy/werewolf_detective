# Werewolf Detective: AI Debate & Lie Detection

นักสืบ (ไม่รู้คำตอบ) ถกเถียง 3 รอบกับผู้ต้องสงสัย 2 คน คนหนึ่งคือหมาป่า (รู้ว่าตัวเองผิดและโกหกได้)
อีกคนเป็นผู้บริสุทธิ์ จากนั้นสภาชาวบ้าน (โมเดลที่อ่อนกว่า) โหวต **โดยไม่เห็นแฟ้มคดี**
สภาเห็นแค่บทถกเถียง และทุกการอ้างหลักฐาน `[E#: ...]` ถูกโค้ดตรวจแล้วติดป้าย
`(verified)` / `(MISQUOTED)` / `(NOT IN CASE FILE)`

ทุกคดีถูกตรวจด้วย solver ในโค้ด (`cases.solve`) ว่ามีคำตอบได้คนเดียวเท่านั้น

## การออกแบบ (prompt v2)

| ใคร | เห็นอะไร | หน้าที่ |
| --- | --- | --- |
| Detective | แฟ้มคดี + บทถกเถียง | หาคำตอบ, ไม่รู้ว่าใครผิด |
| Wolf | แฟ้มคดี + บทถกเถียง + รู้ว่าตัวเองผิด | ไม่ให้ถูกโหวตออก, โกหกได้ |
| Innocent suspect | แฟ้มคดี + บทถกเถียง | ปกป้องตัวเอง, ช่วยหาหมาป่า (มีไว้กันไม่ให้ "โหวตคนที่พูด" ได้ผล) |
| Council (debate only) | บทถกเถียงที่ติดป้าย citation แล้ว **ไม่เห็นแฟ้ม** | ตัววัดหลัก |
| Judge alone | แฟ้มคดีอย่างเดียว ไม่มี debate | judge ขนาดนี้ทำได้แค่ไหนถ้าอ่านเอง |
| Lie judge | แฟ้มคดี + ประโยคของผู้ต้องสงสัย | ติดป้าย true / false / opinion |

ระดับความยาก (`cases.py`): L0 มีเบาะแสตรง (easy เดิม), L1 hard เดิม, L2 6 คน + ข้อมูลรบกวน,
L3 + alibi ที่จบก่อนเวลาตาย, L4 + เส้นทางเบาะแสทางอ้อมและเบาะแสหลอกที่แรงขึ้น
ดูตัวอย่าง: `python cases.py L1 L3 L4`

## ไฟล์

| ไฟล์ | หน้าที่ |
| --- | --- |
| `cases.py` | สร้างแฟ้มคดีตามระดับ + solver ตรวจว่าไม่กำกวม |
| `prompts.py` | prompt ของทุกบทบาท (เปลี่ยนเมื่อไรให้เพิ่ม `PROMPT_VERSION`) |
| `backends.py` | วิธีเรียกโมเดล: `cli` (claude -p), `api`, `mock` |
| `checker.py` | ตรวจ citation และติดป้ายให้สภา |
| `game.py` | เกม 1 เกม + `judge_game()` ให้สภาโหวต |
| `run.py` | รันหลายเกม บันทึกทีละเกม รันต่อจากจุดที่หยุดได้ |
| `pilot.py` | ปรับระดับความยากแบบถูก (2 calls ต่อคดี ไม่มี debate) |
| `rejudge.py` | ให้ judge ขนาดอื่นโหวตบทถกเถียงเดิม โดยไม่ต้องรัน debate ใหม่ |
| `analyze.py` | ตัววัดทั้งหมด พร้อม 95% bootstrap CI |

## วิธีรัน

ต้องมี Python 3.9+

**1. ทดสอบฟรี (ไม่เรียกโมเดล)**
```bash
python run.py --backend mock --cases 4 --out test
python rejudge.py --backend mock --games test/games.jsonl --judges sonnet opus
python analyze.py test/games.jsonl
```

**2. ปรับความยาก** (ทำก่อนรันจริง, ใช้ seed คนละชุดกับการรันจริง)
```bash
unset ANTHROPIC_API_KEY
python pilot.py --backend cli --levels L1 L2 L3 L4 --per-level 10
```
เลือกระดับที่ทั้ง detective และ judge ถูกอยู่ระหว่างโอกาสสุ่มกับ 100% อย่างชัดเจน

**3. เกมจริง** (ต้อง login Claude Code และ *ห้าม* ตั้ง `ANTHROPIC_API_KEY` ถ้าจะใช้แพ็กเกจ)
```bash
python run.py --backend cli --cases 5 --levels L1 L3
python analyze.py results/games.jsonl
```
1 เกมเรียกโมเดลประมาณ 16 ครั้ง ถ้าชนลิมิตกลางทาง ให้รอรีเซ็ตแล้วรันคำสั่งเดิมซ้ำ

**4. เพิ่มแกนขนาด judge**
```bash
python rejudge.py --backend cli --judges sonnet opus
python rejudge.py --backend cli --judges opus --votes 1 --limit 100   # ประหยัดกว่า
```
ต่อเกมต่อ judge ใช้ `votes + 1` calls ผลอยู่ใน `judgements.jsonl` และ `analyze.py` อ่านให้เอง

**5. รันจริงด้วยเครดิต API**
```bash
pip install anthropic
export ANTHROPIC_API_KEY=...
python run.py --backend api --cases 100 --levels L1 L3
```

## หมายเหตุ

- `results/v1_pilot/` คือเกมทดลองแรกจากการออกแบบ v1 (สภาเห็นแฟ้มคดี) `analyze.py` ข้ามเกม v1 ให้
- ตัวเลขจาก mock เป็นค่าสุ่ม ใช้ทดสอบโค้ดเท่านั้น
- อ่าน `results/games.jsonl` ด้วยตาตัวเองก่อนเชื่อตัวเลข
- Claude ช่วยเขียนโค้ดในโปรเจกต์นี้
