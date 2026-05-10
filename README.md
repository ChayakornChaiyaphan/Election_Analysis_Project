# Election Spatial Dashboard

Streamlit dashboard สำหรับ visualize ผลเลือกตั้งรายหน่วย จังหวัดเชียงใหม่ เขต 7 ด้วย `pydeck`.

## วิธีรัน

```bash
cd election_streamlit_dashboard
pip install -r requirements.txt
streamlit run streamlit_election_dashboard.py
```

## ไฟล์ข้อมูล

วางไฟล์ CSV ในโฟลเดอร์ `raw/`:

- `chiangmai_district_7_66.csv`
- `party_list.csv`
- `constituency.csv`
- `party_list2.csv`
- `constituency2.csv`

## หมายเหตุเรื่องพิกัด

ไฟล์ CSV ชุดนี้ยังไม่มี latitude/longitude จริงของแต่ละหน่วยเลือกตั้ง ดังนั้น dashboard ใช้พิกัดประมาณจากตำบลแล้วทำ jitter เพื่อไม่ให้จุดทับกัน หากมีพิกัดจริงให้เพิ่ม column `latitude`, `longitude` แล้วปรับ function `approximate_latlon()` ในไฟล์ Python.

## Layer ที่มี

- ScatterplotLayer: จุดรายหน่วย สีตามพรรคที่ชนะ
- HexagonLayer: density ของหน่วยเลือกตั้ง / ผู้มาใช้สิทธิ
- HeatmapLayer: optional layer
- Tooltip รายหน่วย
- Ranking พรรคที่ชนะรายหน่วย
- Hot areas จาก margin ที่แคบที่สุด
- Detail table คะแนนทั้งหมดของหน่วยที่เลือก
