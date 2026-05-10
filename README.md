# Chiang Mai Election BI Dashboard

โปรเจกต์นี้เป็นระบบเตรียมข้อมูลและวิเคราะห์ผลเลือกตั้ง **จังหวัดเชียงใหม่ เขตเลือกตั้งที่ 7** ครอบคลุมพื้นที่หลัก 3 อำเภอ ได้แก่ **ฝาง**, **แม่อาย** และ **ไชยปราการ** โดยเริ่มจากการสกัดข้อมูลจากไฟล์ PDF/OCR, ทำความสะอาดข้อมูล, ตรวจสอบความถูกต้อง, รวมข้อมูลปี 2566 และ 2569 แล้วนำไปสร้าง Dashboard สำหรับวิเคราะห์ผลเลือกตั้งเชิงพื้นที่และเชิงสถิติ

---

## Project Overview

เป้าหมายของโปรเจกต์คือแปลงข้อมูลเลือกตั้งที่อยู่ในรูปแบบ PDF/ไฟล์ดิบให้กลายเป็นข้อมูลเชิงโครงสร้างที่สามารถนำไปวิเคราะห์ต่อได้ง่าย เช่น CSV และ Dashboard โดยใช้ Python และ Streamlit

ผลลัพธ์หลักของโปรเจกต์คือ

- ข้อมูลเลือกตั้งที่ผ่านการ clean และ validation
- ข้อมูลรวมคะแนนระดับหน่วยเลือกตั้ง
- ข้อมูลจำนวนบัตร เช่น บัตรดี บัตรเสีย ไม่เลือกผู้ใด และผู้มาใช้สิทธิ
- Dashboard สำหรับดูผลเลือกตั้งรายตำบล รายหน่วย และเปรียบเทียบปี 2566 กับ 2569
- Statistical insight เช่น margin, turnout, invalid ballot, no vote, ticket splitting และ education level analysis

---
```

> หมายเหตุ: Dashboard จะอ่าน `final_with_ballots_2566_2569_combined_clean.csv` เป็นหลัก ถ้าไม่พบไฟล์นี้จะ fallback ไปใช้ `final_2566_2569_combined_clean.csv`

---

### `election_de_pipeline_final.ipynb`

Notebook สำหรับ Data Preparation / Data Engineering ใช้เตรียมข้อมูลก่อนนำเข้า Dashboard

สิ่งที่ทำหลัก ๆ ได้แก่

- อ่านข้อมูลดิบจาก OCR/CSV
- แปลง JSON เป็น CSV
- Clean ชื่อพรรค ชื่อพื้นที่ และชื่อ column
- สร้าง `unit_index` เพื่อใช้เชื่อมข้อมูลระดับหน่วยเลือกตั้ง
- รวมข้อมูลแบ่งเขตและบัญชีรายชื่อ
- Join ข้อมูลจำนวนบัตร
- คำนวณตัวชี้วัด เช่น turnout rate, invalid rate, no-vote rate และ margin rate
- สร้าง audit flags เพื่อตรวจหน่วยที่ข้อมูลอาจผิดปกติ
- รวมข้อมูลปี 2566 และ 2569 ให้อยู่ใน schema เดียวกัน
- Export final CSV สำหรับใช้ใน Dashboard

### `streamlit_election_dashboard.py`

ไฟล์หลักสำหรับรัน Dashboard ด้วย Streamlit

Dashboard ประกอบด้วย tab หลัก ๆ ดังนี้

- `Map`
- `Ranking`
- `Subdistrict Detail`
- `Education Level`
- `เขต vs บชรายชื่อ`
- `Statistics Insight`
- `Raw / Debug`

---

## Installation

ติดตั้ง package ที่จำเป็น

```bash
pip install streamlit pandas numpy plotly pydeck scipy
```

```bash
pip install -r requirements.txt
```

---

## How to Run

รัน Dashboard ด้วยคำสั่ง

```bash
streamlit run streamlit_election_dashboard.py
```

จากนั้นเปิด browser ตาม URL ที่ Streamlit แสดง เช่น

```text
http://localhost:8501
```

---

## Required Data Files

วางไฟล์ข้อมูลในโฟลเดอร์ `raw/`

### 1. Election Final Data

```text
raw/final_with_ballots_2566_2569_combined_clean.csv
```

เป็นไฟล์หลักที่ Dashboard ใช้ โดยควรมี column สำคัญ เช่น

```text
unit_index
year
election_type
unit_type
district
subdistrict
village_no
precinct_no
set_no
winner_party
winner_candidate
winner_votes
runner_up_party
runner_up_votes
margin
total_votes_in_file
results
display_name
eligible_voters
appeared_voters
used_ballots
valid_ballots
invalid_ballots
no_vote_ballots
remaining_ballots
audit_level
```

### 2. GeoJSON

```text
raw/tha_admin3.geojson
```

ใช้สำหรับวาดแผนที่ระดับตำบลในเชียงใหม่

### 3. Education Data

```text
raw/education_by_agency_district_year.csv
```

ใช้สำหรับคำนวณระดับการศึกษาเฉลี่ยรายอำเภอและเปรียบเทียบช่วงปี

---

## Data Preparation Methods

### 1. Winner / Runner-up / Margin

สรุปคะแนนรายหน่วยเลือกตั้งเพื่อหาผู้ชนะ อันดับสอง และส่วนต่างคะแนน

สร้าง column เช่น

```text
winner_party
winner_candidate
winner_votes
runner_up_party
runner_up_votes
margin
total_votes_in_file
results
```

โดย `margin` คำนวณจาก

```text
margin = winner_votes - runner_up_votes
```

และ `results` เก็บคะแนนของทุกพรรค/ผู้สมัครในหน่วยนั้นแบบเรียงอันดับ

### 2. Join Ballot Counts

นำข้อมูลจำนวนบัตรมาเชื่อมกับข้อมูลคะแนนระดับหน่วยเลือกตั้ง เช่น

```text
eligible_voters
appeared_voters
allocated_ballots
used_ballots
valid_ballots
invalid_ballots
no_vote_ballots
remaining_ballots
```

การ join ใช้ key ระดับหน่วยเลือกตั้ง เช่น อำเภอ ตำบล หมู่ และหมายเลขหน่วยเลือกตั้ง เพื่อให้ข้อมูลคะแนนและข้อมูลจำนวนบัตรอยู่ในแถวเดียวกัน

### 3. Rate Calculation

หลังจาก join จำนวนบัตรแล้ว จะคำนวณ rate เพิ่มเพื่อใช้วิเคราะห์และเปรียบเทียบพื้นที่

```text
turnout_rate = appeared_voters / eligible_voters * 100
used_ballot_rate = used_ballots / allocated_ballots * 100
valid_rate = valid_ballots / used_ballots * 100
invalid_rate = invalid_ballots / used_ballots * 100
no_vote_rate = no_vote_ballots / used_ballots * 100
winner_share = winner_votes / total_votes_in_file * 100
margin_rate = margin / total_votes_in_file * 100
```

### 4. Audit Flags

สร้าง flags เพื่อตรวจหน่วยเลือกตั้งที่ข้อมูลอาจผิดปกติ เช่น

- คะแนนรวมไม่ตรงกับบัตรดี
- ผู้มาใช้สิทธิมากกว่าผู้มีสิทธิ
- บัตรใช้แล้วมากกว่าบัตรที่ได้รับจัดสรร
- ผลรวมบัตรดี + บัตรเสีย + ไม่เลือกผู้ใด ไม่ตรงกับบัตรใช้แล้ว
- turnout rate สูงผิดปกติ
- invalid rate หรือ no-vote rate สูงผิดปกติ

เป้าหมายคือช่วยระบุหน่วยที่ควรกลับไปตรวจ OCR หรือไฟล์ต้นฉบับซ้ำ ไม่ได้สรุปว่าข้อมูลผิดแน่นอน

### 5. Audit Level

จัดระดับหน่วยเลือกตั้งตามจำนวนและความรุนแรงของ flags เป็น

```text
ok
review
high_review
```

แนวคิดคือ

```text
ไม่มี flag สำคัญ        -> ok
มี flag เล็กน้อย       -> review
มี serious flag หลายข้อ -> high_review
```

---

## Dashboard Features

### 1. Map

แสดงแผนที่รายตำบลด้วย `pydeck` โดยใช้สีตามพรรคที่ชนะ

โหมดการแสดงผล ได้แก่

- แสดงตามปีที่เลือก
- แสดงตำบลสีเดิม
- แสดงตำบลเปลี่ยนสี
- แข่งขันดุ
- ชนะขาด

เกณฑ์ที่ใช้

```text
แข่งขันดุ = margin <= 5%
ชนะขาด = margin >= 15%
```

### 2. Ranking

แสดง ranking พรรคที่ชนะมากที่สุด เช่น

- จำนวนพื้นที่/ชุดที่แต่ละพรรคชนะ
- จำนวนตำบลที่แต่ละพรรคชนะ
- จำนวนหน่วยเลือกตั้งที่แต่ละพรรคชนะ แยกตามตำบล
- ตำบลที่แข่งขันดุ
- ตำบลที่ชนะขาด
- ล่วงหน้านอกเขต / นอกราชอาณาจักร รายชุด

### 3. Subdistrict Detail

ดูรายละเอียดเฉพาะตำบล เช่น

- พรรคที่ชนะ
- คะแนนผู้ชนะ
- พรรคอันดับสอง
- margin
- total votes
- คะแนนรวมรายพรรคในตำบล
- รายการหน่วยเลือกตั้งในตำบลนั้น

### 4. Education Level

คำนวณระดับการศึกษาเฉลี่ยโดยใช้ score แบบ fix

| ระดับการศึกษา | คะแนน |
|---|---:|
| ก่อนประถมศึกษา | 1 |
| ประถมศึกษา | 2 |
| มัธยมศึกษาตอนต้น | 3 |
| มัธยมศึกษาตอนปลาย / ปวช. | 4 |
| ปวส. / สูงกว่า | 5 |

สูตรที่ใช้

```text
education_score =
sum(จำนวนคนในแต่ละระดับ * คะแนนระดับการศึกษา)
/
sum(จำนวนคนทั้งหมด)
```

ใช้วิเคราะห์

- ระดับการศึกษาเฉลี่ยทั้งจังหวัด
- เปรียบเทียบรายอำเภอ
- เปรียบเทียบช่วงปี 64-66 กับ 67-68
- ความสัมพันธ์เบื้องต้นระหว่างระดับการศึกษาเฉลี่ยกับพรรคที่ชนะ

### 5. Constituency vs Party-list

เปรียบเทียบคะแนน **สส เขต** กับ **บัญชีรายชื่อ**

ใช้ดูว่าคนในพื้นที่มีแนวโน้ม

- เลือกคนมากกว่าพรรค
- เลือกพรรคมากกว่าคน
- คะแนนสองบัตรไปในทิศทางเดียวกันหรือไม่

สูตรหลัก

```text
person_minus_party_votes = constituency_votes - partylist_votes
```

การตีความ

```text
ค่าบวก = สส เขต มากกว่า บชรายชื่อ
ค่าลบ = บชรายชื่อ มากกว่า สส เขต
```

กราฟแนวโน้มใช้หลักการ

```text
1 จุด = 1 หน่วยเลือกตั้งในแต่ละตำบล
แกน X = คะแนนบัญชีรายชื่อ
แกน Y = คะแนน สส เขต
```

### 6. Statistics Insight

รวม visualization และสถิติที่น่าสนใจ เช่น

- Descriptive statistics
- Voter turnout analysis
- Invalid ballot / no vote analysis
- Winner analysis
- Margin distribution analysis
- Paired T-Test
- Ticket splitting correlation

---

## Statistical Methods

### Margin Distribution Analysis

วิเคราะห์ส่วนต่างคะแนนระหว่างอันดับ 1 กับอันดับ 2 เพื่อแยกพื้นที่ที่แข่งขันดุหรือชนะขาด

```text
margin_pct = margin / total_votes_in_file * 100
```

เกณฑ์

```text
margin_pct <= 5%  -> แข่งขันดุ
margin_pct >= 15% -> ชนะขาด
```

### Paired T-Test

ใช้เปรียบเทียบคะแนน สส เขต กับบัญชีรายชื่อของพรรคเดียวกันในหน่วยเดียวกัน เพื่อดูว่าคะแนนสองบัตรแตกต่างกันอย่างมีนัยสำคัญหรือไม่

```text
H0: คะแนน สส เขต และบัญชีรายชื่อไม่แตกต่างกัน
H1: คะแนน สส เขต และบัญชีรายชื่อแตกต่างกัน
```

### Pearson Correlation

ใช้ดูความสัมพันธ์ระหว่างคะแนน สส เขต และบัญชีรายชื่อ

```text
r ใกล้ 1  -> คะแนนสองบัตรไปในทิศทางเดียวกันสูง
r ใกล้ 0  -> ความสัมพันธ์ต่ำ
r ติดลบ  -> แนวโน้มสวนทางกัน
```

## Technologies Used

- Python
- pandas
- NumPy
- Plotly
- Pydeck
- Streamlit
- SciPy
- GeoJSON

---

## Output

ผลลัพธ์สุดท้ายของโปรเจกต์คือ Dashboard ที่สามารถใช้เพื่อ

- ดูผลเลือกตั้งเชิงพื้นที่
- เปรียบเทียบปี 2566 กับ 2569
- วิเคราะห์พฤติกรรมเลือกคน vs เลือกพรรค
- ตรวจพื้นที่แข่งขันดุหรือชนะขาด
- วิเคราะห์ turnout, invalid ballot และ no vote
- เชื่อมโยงข้อมูลการศึกษากับผลเลือกตั้ง
- Export raw และ summary data สำหรับวิเคราะห์ต่อ

---

## Team

DSDE Project No. 07  
Chiang Mai Election 2026

สมาชิก

- Kitkanaporn Umpaimungkorn
- Chayakorn Chaiyaphan
- Nasapon Pitoonmanit
