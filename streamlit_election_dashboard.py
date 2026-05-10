from __future__ import annotations

import ast
import html
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components


# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Thai Election BI Dashboard",
    layout="wide",
)

st.title("Thai Election BI Dashboard")
st.caption("แผนที่แบ่งสีตามพรรคที่ชนะในแต่ละตำบล")


# =========================================================
# PATH
# =========================================================
APP_DIR = Path(__file__).resolve().parent

DATA_PATH = APP_DIR / "raw" / "final_with_ballots_2566_2569_combined_clean.csv"

if not DATA_PATH.exists():
    DATA_PATH = APP_DIR / "raw" / "final_2566_2569_combined_clean.csv"

GEOJSON_PATH = APP_DIR / "raw" / "tha_admin3.geojson"
EDU_PATH = APP_DIR / "raw" / "education_by_agency_district_year.csv"


# =========================================================
# MAP STYLE
# =========================================================
MAP_STYLES = {
    "Light": "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Dark": "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    "Road": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
}


# =========================================================
# PARTY COLORS
# =========================================================
PARTY_COLOR_MAP = {
    "เพื่อไทย": [220, 50, 47, 190],
    "ประชาชน": [255, 145, 36, 190],
    "ก้าวไกล": [255, 145, 36, 190],
    "ภูมิใจไทย": [30, 120, 210, 190],
    "รวมไทยสร้างชาติ": [95, 55, 160, 190],
    "พลังประชารัฐ": [70, 90, 210, 190],
    "ประชาธิปัตย์": [40, 80, 180, 190],
    "กล้าธรรม": [45, 155, 85, 190],
    "ไทยสร้างไทย": [90, 180, 220, 190],
    "เสรีรวมไทย": [230, 190, 40, 190],
    "ชาติไทยพัฒนา": [245, 100, 180, 190],
    "ประชาชาติ": [80, 160, 220, 190],
    "เศรษฐกิจ": [170, 90, 190, 190],
}

DEFAULT_COLOR = [130, 130, 130, 160]
NO_DATA_COLOR = [220, 220, 220, 70]

GREY_COLOR = [170, 170, 170, 85]
GREY_LINE_COLOR = [230, 230, 230, 180]

CLOSE_RACE_THRESHOLD_PCT = 5.0
LANDSLIDE_THRESHOLD_PCT = 15.0

DISPLAY_MODES = [
    "แสดงตามปีที่เลือก",
    "แสดงตำบลสีเดิม",
    "แสดงตำบลเปลี่ยนสี",
    "แข่งขันดุ",
    "ชนะขาด",
]


# =========================================================
# EDUCATION LEVEL CONFIG
# =========================================================
DISTRICT_ORDER = ["ฝาง", "แม่อาย", "ไชยปราการ"]

EDU_PERIOD_YEARS = {
    "ปี 64-66": [2564, 2565, 2566],
    "ปี 67-68": [2567, 2568],
}

ELECTION_YEAR_TO_EDU_PERIOD = {
    2566: "ปี 64-66",
    2569: "ปี 67-68",
}

# Fix score:
# ก่อนประถมศึกษา = 1
# ประถมศึกษา = 2
# มัธยมศึกษาตอนต้น = 3
# มัธยมศึกษาตอนปลาย / ปวช. = 4
# ปวส. / สูงกว่า = 5
EDUCATION_SCORE_MAP = {
    "ก่อนประถมศึกษา": 1,
    "ประถมศึกษา": 2,
    "มัธยมศึกษาตอนต้น": 3,
    "มัธยมศึกษาตอนปลาย": 4,
    "ประกาศนียบัตรวิชาชีพ (ปวช.)": 4,
    "ประกาศนียบัตรวิชาชีพชั้นสูง (ปวส.)": 5,
    "ประกาศนียบัตรบัณฑิตชั้นสูง": 5,
}

PARTY_COLOR_HEX_MAP = {
    "เพื่อไทย": "#dc322f",
    "ประชาชน": "#ff9124",
    "ก้าวไกล": "#ff9124",
    "ภูมิใจไทย": "#1e78d2",
    "รวมไทยสร้างชาติ": "#5f37a0",
    "พลังประชารัฐ": "#465ad2",
    "ประชาธิปัตย์": "#2850b4",
    "กล้าธรรม": "#2d9b55",
    "ไทยสร้างไทย": "#5ab4dc",
    "เสรีรวมไทย": "#e6be28",
    "ชาติไทยพัฒนา": "#f564b4",
    "ประชาชาติ": "#50a0dc",
    "เศรษฐกิจ": "#aa5abe",
}

# ใช้เฉพาะตอนเปรียบเทียบข้ามปีเท่านั้น
# ไม่เปลี่ยนชื่อพรรคจริงในข้อมูล: ปี 2566 ยังเป็น "ก้าวไกล" และปี 2569 ยังเป็น "ประชาชน"
PARTY_COMPARE_ALIAS_MAP = {
    "ก้าวไกล": "move_forward_people",
    "ประชาชน": "move_forward_people",
}

PARTY_COMPARE_LABEL_MAP = {
    "move_forward_people": "ก้าวไกล/ประชาชน",
}

if "display_mode" not in st.session_state:
    st.session_state["display_mode"] = DISPLAY_MODES[0]


# =========================================================
# UTILITY FUNCTIONS
# =========================================================
def format_int(value: Any) -> str:
    try:
        if pd.isna(value):
            return "-"
        return f"{float(value):,.0f}"
    except Exception:
        return "-"


def clean_id(value: Any) -> str:
    if pd.isna(value):
        return ""

    try:
        return str(int(float(value)))
    except Exception:
        return str(value).strip()


def parse_list_value(value: Any) -> list:
    if isinstance(value, list):
        return value

    if pd.isna(value):
        return []

    text = str(value).strip()

    if text == "":
        return []

    try:
        return json.loads(text)
    except Exception:
        pass

    try:
        return ast.literal_eval(text)
    except Exception:
        return []


def normalize_text(value: Any) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    replacements = [
        "จังหวัด",
        "จ.",
        "อำเภอ",
        "อ.",
        "เขต",
        "ตำบล",
        "ต.",
        "แขวง",
        "เทศบาลตำบล",
        "เทศบาล",
        "ทต.",
        "อบต.",
        " ",
        "-",
        "_",
    ]

    for r in replacements:
        text = text.replace(r, "")

    return text.lower()


def canonical_subdistrict(value: Any) -> str:
    if pd.isna(value):
        return ""

    text = str(value).strip()

    mapping = {
        "บ้านแม่ข่า": "แม่ข่า",
        "ทต.บ้านแม่ข่า": "แม่ข่า",
        "เทศบาลตำบลบ้านแม่ข่า": "แม่ข่า",
        "เวียงฝาง": "เวียง",
        "ทต.เวียงฝาง": "เวียง",
        "เทศบาลตำบลเวียงฝาง": "เวียง",
    }

    return mapping.get(text, text)


def make_area_key(district: Any, subdistrict: Any) -> str:
    return normalize_text(district) + "__" + normalize_text(subdistrict)


def get_party_color(party: Any, opacity: int = 180) -> list[int]:
    party_text = canonical_party(party)
    color = PARTY_COLOR_MAP.get(party_text, DEFAULT_COLOR)
    return [color[0], color[1], color[2], opacity]


def rgba_css(color: list[int]) -> str:
    alpha = color[3] / 255 if len(color) >= 4 else 1
    return f"rgba({color[0]}, {color[1]}, {color[2]}, {alpha:.2f})"


def extract_feature_property(props: dict, candidates: list[str]) -> str:
    for key in candidates:
        if key in props and props[key] not in [None, ""]:
            return str(props[key]).strip()
    return ""


def is_advance_unit_series(unit_type_series: pd.Series) -> pd.Series:
    text = unit_type_series.fillna("").astype(str).str.lower()

    return (
        text.str.contains("advance", na=False)
        | text.str.contains("ล่วงหน้า", na=False)
        | text.str.contains("นอกเขต", na=False)
        | text.str.contains("นอกราชอาณาจักร", na=False)
    )


def normalize_results_table(results: list) -> pd.DataFrame:
    result_table = pd.DataFrame(results)

    if result_table.empty:
        return result_table

    if "party" in result_table.columns and "party_name" not in result_table.columns:
        result_table = result_table.rename(columns={"party": "party_name"})

    expected_cols = [
        "rank",
        "party_no",
        "party_name",
        "candidate_no",
        "candidate_name",
        "votes",
    ]

    for col in expected_cols:
        if col not in result_table.columns:
            result_table[col] = ""

    result_table["votes"] = (
        pd.to_numeric(result_table["votes"], errors="coerce")
        .fillna(0)
        .astype(int)
    )

    result_table["rank"] = (
        pd.to_numeric(result_table["rank"], errors="coerce")
        .fillna(9999)
        .astype(int)
    )

    result_table["party_name"] = result_table["party_name"].apply(canonical_party)

    return result_table.sort_values("rank")[expected_cols]


def safe_int(value: Any) -> int:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return 0
    return int(numeric)


def safe_float(value: Any) -> float:
    numeric = pd.to_numeric(value, errors="coerce")
    if pd.isna(numeric):
        return 0.0
    return float(numeric)


def format_number(value: Any, digits: int = 2) -> str:
    try:
        if pd.isna(value):
            return "-"
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "-"


def canonical_party(value: Any) -> str:
    """Clean party name only. Do not merge ก้าวไกล and ประชาชน globally."""
    if pd.isna(value):
        return ""

    text = str(value).strip()

    if text.startswith("พรรค"):
        text = text.replace("พรรค", "", 1).strip()

    return text


def party_compare_key(value: Any) -> str:
    """Key used only when comparing across 2566 and 2569."""
    party = canonical_party(value)
    return PARTY_COMPARE_ALIAS_MAP.get(party, party)


def party_compare_label(value: Any) -> str:
    key = party_compare_key(value)
    return PARTY_COMPARE_LABEL_MAP.get(key, canonical_party(value))


# =========================================================
# EDUCATION LEVEL FUNCTIONS
# =========================================================
def normalize_district(value: Any) -> str:
    text = str(value).strip()

    mapping = {
        "อำเภอฝาง": "ฝาง",
        "ฝาง": "ฝาง",
        "อำเภอแม่อาย": "แม่อาย",
        "แม่อาย": "แม่อาย",
        "ทต.แม่อาย": "แม่อาย",
        "อำเภอไชยปราการ": "ไชยปราการ",
        "ไชยปราการ": "ไชยปราการ",
    }

    if text in mapping:
        return mapping[text]

    text_norm = normalize_text(text)

    if "ฝาง" in text_norm:
        return "ฝาง"

    if "แม่อาย" in text_norm:
        return "แม่อาย"

    if "ไชยปราการ" in text_norm:
        return "ไชยปราการ"

    # ห้ามนับ "เขต 7" เป็นอำเภอ เพราะเป็นชื่อเขตเลือกตั้ง ไม่ใช่อำเภอจริง
    if text_norm in ["เขต7", "เลือกตั้ง7", "เขตเลือกตั้ง7"]:
        return "เขต 7"

    return text


def infer_district_from_subdistrict(df: pd.DataFrame) -> pd.DataFrame:
    """แก้ปัญหาแถวที่ district เป็น 'เขต 7'.

    บางไฟล์โดยเฉพาะบัตรบัญชีรายชื่ออาจใส่ district เป็น 'เขต 7' แทนอำเภอจริง
    ซึ่งทำให้การจับคู่ สส เขต vs บชรายชื่อ ระดับหน่วยเพี้ยน เพราะ key ไม่ตรงกัน
    ฟังก์ชันนี้จะ infer อำเภอจริงจากชื่อตำบล โดยใช้แถวที่มีอำเภอจริงเป็น reference
    และยังเก็บ district_original ไว้ตรวจสอบใน Raw / Debug
    """
    out = df.copy()

    if "district" not in out.columns or "subdistrict" not in out.columns:
        return out

    if "district_original" not in out.columns:
        out["district_original"] = out["district"]

    out["district"] = out["district"].apply(normalize_district)
    out["subdistrict"] = out["subdistrict"].apply(canonical_subdistrict)

    ref = out[
        out["district"].isin(DISTRICT_ORDER)
        & out["subdistrict"].fillna("").astype(str).str.strip().ne("")
    ].copy()

    if ref.empty:
        out["district_inferred_from_subdistrict"] = False
        return out

    district_lookup = (
        ref.groupby("subdistrict")["district"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        .to_dict()
    )

    unknown_mask = (
        ~out["district"].isin(DISTRICT_ORDER)
        & out["subdistrict"].isin(district_lookup.keys())
    )

    out["district_inferred_from_subdistrict"] = unknown_mask
    out.loc[unknown_mask, "district"] = out.loc[unknown_mask, "subdistrict"].map(district_lookup)

    return out


@st.cache_data(show_spinner="Loading education data ...")
def load_education_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()

    df = pd.read_csv(path, encoding="utf-8-sig")

    required_cols = ["สังกัด", "ระดับ"]
    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise ValueError(f"education csv ขาด columns: {missing}")

    df["สังกัด"] = df["สังกัด"].fillna("").astype(str).str.strip()
    df["ระดับ"] = df["ระดับ"].fillna("").astype(str).str.strip()

    df = df[df["ระดับ"].ne("")].copy()

    year_cols = []

    for col in df.columns:
        if "_" not in col:
            continue

        district_part, year_part = col.rsplit("_", 1)

        if year_part.isdigit():
            year_cols.append(col)

    if not year_cols:
        raise ValueError("ไม่พบ column รูปแบบ อำเภอ_ปี เช่น ฝาง_2568")

    long_rows = []

    for col in year_cols:
        district_part, year_part = col.rsplit("_", 1)

        temp = df[["สังกัด", "ระดับ", col]].copy()
        temp = temp.rename(columns={col: "count"})

        temp["district"] = normalize_district(district_part)
        temp["year"] = int(year_part)
        temp["count"] = pd.to_numeric(temp["count"], errors="coerce").fillna(0)

        long_rows.append(temp)

    long_df = pd.concat(long_rows, ignore_index=True)

    long_df = long_df[
        long_df["district"].isin(DISTRICT_ORDER)
        & long_df["year"].between(2564, 2568)
    ].copy()

    return long_df.reset_index(drop=True)


def build_education_average(
    edu_df: pd.DataFrame,
    score_map: dict[str, float],
) -> pd.DataFrame:
    work = edu_df.copy()

    work["level_score"] = work["ระดับ"].map(score_map)

    unknown_levels = sorted(
        work.loc[work["level_score"].isna(), "ระดับ"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    if unknown_levels:
        st.warning(
            "มีระดับการศึกษาที่ไม่มี score map และจะถูกตัดออก: "
            + ", ".join(unknown_levels)
        )

    work = work[work["level_score"].notna()].copy()
    work["weighted_score"] = work["count"] * work["level_score"]

    grouped = (
        work.groupby(["district", "year"], as_index=False)
        .agg(
            total_people=("count", "sum"),
            weighted_score=("weighted_score", "sum"),
        )
    )

    grouped["avg_education_score"] = np.where(
        grouped["total_people"] > 0,
        grouped["weighted_score"] / grouped["total_people"],
        np.nan,
    )

    grouped["avg_education_score"] = grouped["avg_education_score"].round(3)

    return grouped


def build_province_average(edu_avg: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        edu_avg.groupby("year", as_index=False)
        .agg(
            total_people=("total_people", "sum"),
            weighted_score=("weighted_score", "sum"),
        )
    )

    grouped["district"] = "ทั้งจังหวัด"

    grouped["avg_education_score"] = np.where(
        grouped["total_people"] > 0,
        grouped["weighted_score"] / grouped["total_people"],
        np.nan,
    )

    grouped["avg_education_score"] = grouped["avg_education_score"].round(3)

    return grouped[
        [
            "district",
            "year",
            "total_people",
            "weighted_score",
            "avg_education_score",
        ]
    ]


def build_period_average(edu_avg: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for period_name, years in EDU_PERIOD_YEARS.items():
        temp = edu_avg[edu_avg["year"].isin(years)].copy()

        if temp.empty:
            continue

        district_group = (
            temp.groupby("district", as_index=False)
            .agg(
                total_people=("total_people", "sum"),
                weighted_score=("weighted_score", "sum"),
            )
        )

        district_group["period"] = period_name

        district_group["avg_education_score"] = np.where(
            district_group["total_people"] > 0,
            district_group["weighted_score"] / district_group["total_people"],
            np.nan,
        )

        rows.append(district_group)

        province_row = pd.DataFrame(
            {
                "district": ["ทั้งจังหวัด"],
                "total_people": [temp["total_people"].sum()],
                "weighted_score": [temp["weighted_score"].sum()],
                "period": [period_name],
            }
        )

        province_row["avg_education_score"] = np.where(
            province_row["total_people"] > 0,
            province_row["weighted_score"] / province_row["total_people"],
            np.nan,
        )

        rows.append(province_row)

    if not rows:
        return pd.DataFrame()

    out = pd.concat(rows, ignore_index=True)
    out["avg_education_score"] = out["avg_education_score"].round(3)

    return out[
        [
            "district",
            "period",
            "total_people",
            "weighted_score",
            "avg_education_score",
        ]
    ]


def build_level_distribution(edu_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
        edu_df.groupby(["district", "year", "ระดับ"], as_index=False)
        .agg(count=("count", "sum"))
    )

    total = (
        grouped.groupby(["district", "year"], as_index=False)
        .agg(total_people=("count", "sum"))
    )

    out = grouped.merge(total, on=["district", "year"], how="left")

    out["share_pct"] = np.where(
        out["total_people"] > 0,
        out["count"] / out["total_people"] * 100,
        0,
    )

    out["share_pct"] = out["share_pct"].round(2)

    return out


def build_party_votes_by_district_for_education(df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in df.iterrows():
        year = int(row["year"])
        election_type = row["election_type"]
        district = normalize_district(row["district"])

        result_table = normalize_results_table(row["results"])

        if not result_table.empty and "party_name" in result_table.columns:
            for _, r in result_table.iterrows():
                party = canonical_party(r.get("party_name", ""))
                votes = pd.to_numeric(r.get("votes", 0), errors="coerce")

                if party == "" or pd.isna(votes):
                    continue

                records.append(
                    {
                        "year": year,
                        "election_type": election_type,
                        "district": district,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )
        else:
            party = canonical_party(row.get("winner_party", ""))
            votes = pd.to_numeric(row.get("winner_votes", 0), errors="coerce")

            if party != "" and not pd.isna(votes):
                records.append(
                    {
                        "year": year,
                        "election_type": election_type,
                        "district": district,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )

    vote_df = pd.DataFrame(records)

    if vote_df.empty:
        return pd.DataFrame(
            columns=[
                "year",
                "election_type",
                "district",
                "party",
                "votes",
            ]
        )

    out = (
        vote_df.groupby(
            ["year", "election_type", "district", "party"],
            as_index=False,
        )
        .agg(votes=("votes", "sum"))
        .sort_values(
            ["year", "district", "votes"],
            ascending=[True, True, False],
        )
    )

    return out


def build_district_winner_for_education(party_votes: pd.DataFrame) -> pd.DataFrame:
    rows = []

    if party_votes.empty:
        return pd.DataFrame()

    for keys, group in party_votes.groupby(["year", "election_type", "district"]):
        year, election_type, district = keys

        group = group.sort_values("votes", ascending=False).reset_index(drop=True)

        winner = group.iloc[0]
        runner = group.iloc[1] if len(group) > 1 else None

        total_votes = group["votes"].sum()
        winner_votes = winner["votes"]
        runner_votes = runner["votes"] if runner is not None else 0
        margin_votes = winner_votes - runner_votes

        rows.append(
            {
                "election_year": int(year),
                "election_type": election_type,
                "district": district,
                "winner_party": winner["party"],
                "winner_votes": int(winner_votes),
                "runner_up_party": runner["party"] if runner is not None else "-",
                "runner_up_votes": int(runner_votes),
                "total_votes": int(total_votes),
                "winner_share_pct": round(
                    winner_votes / total_votes * 100 if total_votes > 0 else 0,
                    2,
                ),
                "margin_votes": int(margin_votes),
                "margin_pct": round(
                    margin_votes / total_votes * 100 if total_votes > 0 else 0,
                    2,
                ),
                "edu_period": ELECTION_YEAR_TO_EDU_PERIOD.get(int(year), ""),
            }
        )

    return pd.DataFrame(rows)


# =========================================================
# LEGEND FUNCTIONS
# =========================================================
def render_color_legend(items: list[tuple[str, list[int]]]) -> str:
    html_items = []

    for label, color in items:
        label_safe = html.escape(str(label))
        html_items.append(
            f"""
            <div class="legend-item">
                <div class="legend-color" style="background:{rgba_css(color)};"></div>
                <span>{label_safe}</span>
            </div>
            """
        )

    return f"""
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: transparent;
            color: white;
        }}

        .legend-wrap {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px 16px;
            align-items: center;
            font-family: sans-serif;
            color: white;
            padding: 0;
            margin: 0;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 14px;
            font-weight: 700;
            white-space: nowrap;
            color: white;
        }}

        .legend-color {{
            width: 12px;
            height: 12px;
            border-radius: 2px;
            flex: 0 0 auto;
        }}
    </style>

    <div class="legend-wrap">
        {''.join(html_items)}
    </div>
    """


def render_party_legend(parties: list[str]) -> str:
    items = [(party, get_party_color(party, 230)) for party in parties]
    return render_color_legend(items)


def render_advance_party_legend(advance_hex_data: pd.DataFrame) -> str:
    if advance_hex_data.empty or "winner_party" not in advance_hex_data.columns:
        return ""

    parties = (
        advance_hex_data["winner_party"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .unique()
        .tolist()
    )

    return render_party_legend(parties)


def render_mode_legend(display_mode: str, parties: list[str]) -> str:
    if display_mode == "แสดงตำบลสีเดิม":
        return render_color_legend(
            [
                ("สีพรรค = ตำบลที่พรรคชนะเหมือนเดิม", get_party_color("กล้าธรรม", 230)),
                ("สีเทา = ไม่เข้าเงื่อนไข", GREY_COLOR),
            ]
        )

    if display_mode == "แสดงตำบลเปลี่ยนสี":
        return render_color_legend(
            [
                ("พื้นที่ = พรรคที่ชนะปี 69", get_party_color("กล้าธรรม", 230)),
                ("เส้นขอบ = พรรคที่ชนะปี 66", get_party_color("เพื่อไทย", 255)),
                ("สีเทา = ไม่เข้าเงื่อนไข", GREY_COLOR),
            ]
        )

    if display_mode == "แข่งขันดุ":
        return render_color_legend(
            [
                ("สีพรรค = แข่งขันดุ ≤ 5%", get_party_color("กล้าธรรม", 230)),
                ("สีเทา = ไม่เข้าเงื่อนไข", GREY_COLOR),
            ]
        )

    if display_mode == "ชนะขาด":
        return render_color_legend(
            [
                ("สีพรรค = ชนะขาด ≥ 15%", get_party_color("กล้าธรรม", 230)),
                ("สีเทา = ไม่เข้าเงื่อนไข", GREY_COLOR),
            ]
        )

    return render_party_legend(parties)


# =========================================================
# ADVANCE HEXAGON CHART FUNCTIONS
# =========================================================
def build_advance_set_stats(df: pd.DataFrame, selected_type: str) -> pd.DataFrame:
    advance_df = df[
        (df["election_type"] == selected_type)
        & is_advance_unit_series(df["unit_type"])
    ].copy()

    if advance_df.empty:
        return pd.DataFrame()

    advance_df["set_no_clean"] = advance_df["set_no"].apply(clean_id)

    numeric_cols = [
        "winner_votes",
        "runner_up_votes",
        "margin",
        "total_votes_in_file",
    ]

    for col in numeric_cols:
        if col not in advance_df.columns:
            advance_df[col] = 0

        advance_df[col] = pd.to_numeric(
            advance_df[col],
            errors="coerce",
        ).fillna(0)

    advance_df = advance_df.sort_values(
        by="set_no_clean",
        key=lambda s: pd.to_numeric(s, errors="coerce").fillna(9999),
    )

    return advance_df.reset_index(drop=True)


def make_hexagon_polygon(cx: float, cy: float, r: float = 1.0) -> list[list[float]]:
    points = []

    for angle_deg in [30, 90, 150, 210, 270, 330]:
        angle_rad = np.deg2rad(angle_deg)
        points.append(
            [
                cx + r * np.cos(angle_rad),
                cy + r * np.sin(angle_rad),
            ]
        )

    points.append(points[0])
    return points


def build_advance_hex_layer_data(
    advance_df: pd.DataFrame,
    opacity: int = 180,
) -> pd.DataFrame:
    if advance_df.empty:
        return pd.DataFrame()

    rows = []

    r = 1.0
    dx = np.sqrt(3) * r
    dy = 1.5 * r

    positions = [
        (0 * dx, 2 * dy),
        (1 * dx, 2 * dy),
        (2 * dx, 2 * dy),
        (0.5 * dx, 1 * dy),
        (1.5 * dx, 1 * dy),
        (2.5 * dx, 1 * dy),
        (0 * dx, 0 * dy),
        (1 * dx, 0 * dy),
        (2 * dx, 0 * dy),
    ]

    plot_df = advance_df.head(9).copy().reset_index(drop=True)

    for i, row in plot_df.iterrows():
        cx, cy = positions[i]

        party = canonical_party(row.get("winner_party", "-"))
        color = get_party_color(party, opacity)

        winner_votes = safe_int(row.get("winner_votes", 0))
        total_votes = safe_int(row.get("total_votes_in_file", 0))

        winner_share = (
            round((winner_votes / total_votes * 100), 1)
            if total_votes > 0
            else 0.0
        )

        rows.append(
            {
                "set_no": str(row.get("set_no_clean", i + 1)),
                "unit_type": str(row.get("unit_type", "-")),
                "winner_party": party,
                "winner_votes": winner_votes,
                "runner_up_party": str(row.get("runner_up_party", "-")),
                "runner_up_votes": safe_int(row.get("runner_up_votes", 0)),
                "margin": safe_int(row.get("margin", 0)),
                "total_votes": total_votes,
                "winner_share": winner_share,
                "fill_color": color,
                "polygon": make_hexagon_polygon(cx, cy, r),
            }
        )

    return pd.DataFrame(rows)


def render_advance_hex_plotly(advance_hex_data: pd.DataFrame) -> go.Figure:
    fig = go.Figure()

    for _, row in advance_hex_data.iterrows():
        polygon = row["polygon"]

        x = [p[0] for p in polygon]
        y = [p[1] for p in polygon]

        fill_color = rgba_css(row["fill_color"])

        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                fill="toself",
                fillcolor=fill_color,
                line=dict(
                    color="white",
                    width=2,
                ),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        polygon_no_close = polygon[:-1]
        cx = float(np.mean([p[0] for p in polygon_no_close]))
        cy = float(np.mean([p[1] for p in polygon_no_close]))

        customdata = [
            [
                row.get("set_no", "-"),
                row.get("winner_party", "-"),
                row.get("winner_votes", 0),
                row.get("total_votes", 0),
                row.get("winner_share", 0),
            ]
        ]

        fig.add_trace(
            go.Scatter(
                x=[cx],
                y=[cy],
                mode="markers",
                marker=dict(
                    size=86,
                    color="rgba(255,255,255,0.01)",
                    line=dict(width=0),
                ),
                customdata=customdata,
                hovertemplate=(
                    "<b>ชุด:</b> %{customdata[0]}<br>"
                    "─────────────<br>"
                    "<b>Winner:</b> %{customdata[1]}<br>"
                    "<b>Winner votes:</b> %{customdata[2]:,}<br>"
                    "<b>Total votes:</b> %{customdata[3]:,}<br>"
                    "<b>Winner share:</b> %{customdata[4]}%<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        height=360,
        width=560,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        dragmode=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="black",
            font_color="white",
            font_size=13,
        ),
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            fixedrange=True,
            scaleanchor="y",
            scaleratio=1,
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            fixedrange=True,
        ),
    )

    fig.update_xaxes(range=[-1.2, 5.6])
    fig.update_yaxes(range=[-1.2, 4.6])

    return fig


# =========================================================
# LOAD DATA
# =========================================================
@st.cache_data(show_spinner="Loading election data ...")
def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {DATA_PATH}\n"
            "ให้วางไฟล์ final_with_ballots_2566_2569_combined_clean.csv "
            "หรือ final_2566_2569_combined_clean.csv ไว้ในโฟลเดอร์ raw/"
        )

    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    required_cols = [
        "unit_index",
        "year",
        "election_type",
        "unit_type",
        "district",
        "subdistrict",
        "winner_party",
        "winner_votes",
        "runner_up_party",
        "runner_up_votes",
        "margin",
        "total_votes_in_file",
        "results",
        "display_name",
    ]

    missing = [col for col in required_cols if col not in df.columns]

    if missing:
        raise ValueError(f"final csv ขาด columns: {missing}")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df = df[df["year"].isin([2566, 2569])].copy()

    for col in ["precinct_no", "set_no", "village_no"]:
        if col in df.columns:
            df[col] = df[col].apply(clean_id)
        else:
            df[col] = ""

    text_cols = [
        "unit_index",
        "election_type",
        "unit_type",
        "district",
        "subdistrict",
        "winner_party",
        "winner_candidate",
        "runner_up_party",
        "display_name",
    ]

    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str).str.strip()
        else:
            df[col] = ""

    df["winner_party"] = df["winner_party"].apply(canonical_party)
    df["runner_up_party"] = df["runner_up_party"].apply(canonical_party)

    # Normalize location and fix rows where district is stored as "เขต 7" instead of real amphoe.
    # This is important for matching constituency and party-list rows at polling-unit level.
    df["subdistrict"] = df["subdistrict"].apply(canonical_subdistrict)
    df = infer_district_from_subdistrict(df)

    numeric_cols = [
        "winner_votes",
        "runner_up_votes",
        "margin",
        "total_votes_in_file",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["results"] = df["results"].apply(parse_list_value)

    empty_display = df["display_name"].eq("") | df["display_name"].isna()

    df.loc[empty_display, "display_name"] = (
        "ปี "
        + df.loc[empty_display, "year"].fillna(0).astype(int).astype(str)
        + " / "
        + df.loc[empty_display, "election_type"].astype(str)
        + " / "
        + df.loc[empty_display, "district"].astype(str)
        + " / "
        + df.loc[empty_display, "subdistrict"].astype(str)
        + " / หน่วย "
        + df.loc[empty_display, "precinct_no"].astype(str)
    )

    df["area_key"] = df.apply(
        lambda row: make_area_key(row["district"], row["subdistrict"]),
        axis=1,
    )

    return df.reset_index(drop=True)


@st.cache_data(show_spinner="Loading tha_admin3.geojson ...")
def load_geojson() -> dict:
    if not GEOJSON_PATH.exists():
        raise FileNotFoundError(
            f"ไม่พบไฟล์ {GEOJSON_PATH}\n"
            "ให้วางไฟล์ tha_admin3.geojson ไว้ในโฟลเดอร์ raw/"
        )

    with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


try:
    data = load_data()
    base_geojson = load_geojson()
    edu_long = load_education_data(EDU_PATH)
except Exception as e:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {e}")
    st.stop()

if data.empty:
    st.error("ไม่มีข้อมูลปี 2566 หรือ 2569")
    st.stop()


# =========================================================
# FILTER GEOJSON TO CHIANG MAI
# =========================================================
def filter_chiangmai_geojson(geojson: dict) -> dict:
    out = deepcopy(geojson)
    features = []

    for feature in out.get("features", []):
        props = feature.get("properties", {})
        adm1_th = str(props.get("adm1_name1", "")).strip()
        adm1_en = str(props.get("adm1_name", "")).strip().lower()

        if adm1_th == "เชียงใหม่" or adm1_en == "chiang mai":
            features.append(feature)

    out["features"] = features

    return out


base_geojson = filter_chiangmai_geojson(base_geojson)


# =========================================================
# SIDEBAR
# =========================================================
st.sidebar.header("Filters")

year_options = sorted(
    data["year"]
    .dropna()
    .astype(int)
    .unique()
    .tolist()
)

selected_year = st.sidebar.radio(
    "เลือกปีเลือกตั้ง",
    options=year_options,
    format_func=lambda x: f"ปี {x}",
    horizontal=True,
)

year_filtered = data[data["year"] == selected_year].copy()

election_type_options = sorted(
    year_filtered["election_type"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_type = st.sidebar.radio(
    "เลือกประเภทบัตร",
    options=election_type_options,
    format_func=lambda x: "บัญชีรายชื่อ" if x == "partylist" else "แบ่งเขต",
    horizontal=True,
)

type_filtered = year_filtered[year_filtered["election_type"] == selected_type].copy()

unit_type_options = ["All"] + sorted(
    type_filtered["unit_type"]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)

selected_unit_type = st.sidebar.selectbox(
    "Unit Type",
    unit_type_options,
)

if selected_unit_type != "All":
    area_source = type_filtered[type_filtered["unit_type"] == selected_unit_type].copy()
else:
    area_source = type_filtered.copy()

district_options = ["All"] + sorted(
    area_source["district"]
    .dropna()
    .astype(str)
    .str.strip()
    .replace("", np.nan)
    .dropna()
    .unique()
    .tolist()
)

selected_district = st.sidebar.selectbox(
    "District / Area",
    district_options,
)

if selected_district != "All":
    subdistrict_source = area_source[area_source["district"] == selected_district].copy()
else:
    subdistrict_source = area_source.copy()

subdistrict_options = ["All"] + sorted(
    subdistrict_source["subdistrict"]
    .dropna()
    .astype(str)
    .str.strip()
    .replace("", np.nan)
    .dropna()
    .unique()
    .tolist()
)

selected_subdistrict = st.sidebar.selectbox(
    "Subdistrict",
    subdistrict_options,
)

search_text = st.sidebar.text_input(
    "Search",
    placeholder="ค้นหาอำเภอ / ตำบล / พรรค",
)

st.sidebar.header("Map Settings")

map_style = st.sidebar.selectbox(
    "Map Style",
    options=list(MAP_STYLES.keys()),
    index=0,
)

line_width = st.sidebar.slider(
    "Boundary Width",
    min_value=1,
    max_value=5,
    value=1,
    step=1,
)

fill_opacity = st.sidebar.slider(
    "Fill Opacity",
    min_value=50,
    max_value=230,
    value=180,
    step=10,
)

display_mode = st.session_state.get("display_mode", DISPLAY_MODES[0])


# =========================================================
# APPLY FILTERS
# =========================================================
def apply_dashboard_filters(
    source_df: pd.DataFrame,
    year: int,
    election_type: str,
    unit_type: str = "All",
    district: str = "All",
    subdistrict: str = "All",
    search: str = "",
) -> pd.DataFrame:
    filtered = source_df[
        (source_df["year"] == year)
        & (source_df["election_type"] == election_type)
    ].copy()

    if unit_type != "All":
        filtered = filtered[filtered["unit_type"] == unit_type].copy()

    if district != "All":
        filtered = filtered[filtered["district"] == district].copy()

    if subdistrict != "All":
        filtered = filtered[filtered["subdistrict"] == subdistrict].copy()

    if search.strip():
        q = search.strip().lower()

        search_col = (
            filtered["district"].astype(str)
            + " "
            + filtered["subdistrict"].astype(str)
            + " "
            + filtered["winner_party"].astype(str)
            + " "
            + filtered["runner_up_party"].astype(str)
            + " "
            + filtered["unit_index"].astype(str)
        ).str.lower()

        filtered = filtered[search_col.str.contains(q, na=False)].copy()

    return filtered


filtered_data = apply_dashboard_filters(
    source_df=data,
    year=selected_year,
    election_type=selected_type,
    unit_type=selected_unit_type,
    district=selected_district,
    subdistrict=selected_subdistrict,
    search=search_text,
)

if filtered_data.empty:
    st.warning("ไม่มีข้อมูลตาม filter ที่เลือก")
    st.stop()


# =========================================================
# AGGREGATION FUNCTIONS
# =========================================================
def build_party_votes_by_area(df: pd.DataFrame) -> pd.DataFrame:
    records = []

    for _, row in df.iterrows():
        area_key = row["area_key"]
        district = row["district"]
        subdistrict = row["subdistrict"]

        result_table = normalize_results_table(row["results"])

        if not result_table.empty and "party_name" in result_table.columns:
            for _, r in result_table.iterrows():
                party = canonical_party(r.get("party_name", ""))
                votes = pd.to_numeric(r.get("votes", 0), errors="coerce")

                if party == "" or pd.isna(votes):
                    continue

                records.append(
                    {
                        "area_key": area_key,
                        "district": district,
                        "subdistrict": subdistrict,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )
        else:
            party = canonical_party(row.get("winner_party", ""))
            votes = pd.to_numeric(row.get("winner_votes", 0), errors="coerce")

            if party != "" and not pd.isna(votes):
                records.append(
                    {
                        "area_key": area_key,
                        "district": district,
                        "subdistrict": subdistrict,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )

    vote_df = pd.DataFrame(records)

    if vote_df.empty:
        return pd.DataFrame(
            columns=[
                "area_key",
                "district",
                "subdistrict",
                "winner_party",
                "winner_votes",
                "runner_up_party",
                "runner_up_votes",
                "margin_votes",
                "total_votes",
                "winner_share",
                "runner_up_share",
                "margin_pct",
            ]
        )

    party_sum = (
        vote_df.groupby(
            ["area_key", "district", "subdistrict", "party"],
            dropna=False,
            as_index=False,
        )
        .agg(votes=("votes", "sum"))
    )

    total_sum = (
        party_sum.groupby("area_key", as_index=False)
        .agg(total_votes=("votes", "sum"))
    )

    rows = []

    for area_key, group in party_sum.groupby("area_key"):
        group = group.sort_values("votes", ascending=False).reset_index(drop=True)

        winner = group.iloc[0]
        runner = group.iloc[1] if len(group) > 1 else None

        total_votes = float(
            total_sum.loc[total_sum["area_key"] == area_key, "total_votes"].iloc[0]
        )
        winner_votes = float(winner["votes"])
        runner_up_votes = float(runner["votes"]) if runner is not None else 0.0

        margin_votes = winner_votes - runner_up_votes
        winner_share = winner_votes / total_votes * 100 if total_votes > 0 else 0
        runner_up_share = runner_up_votes / total_votes * 100 if total_votes > 0 else 0
        margin_pct = margin_votes / total_votes * 100 if total_votes > 0 else 0

        rows.append(
            {
                "area_key": area_key,
                "district": winner["district"],
                "subdistrict": winner["subdistrict"],
                "winner_party": winner["party"],
                "winner_votes": int(winner_votes),
                "runner_up_party": runner["party"] if runner is not None else "-",
                "runner_up_votes": int(runner_up_votes),
                "margin_votes": int(margin_votes),
                "total_votes": int(total_votes),
                "winner_share": round(winner_share, 1),
                "runner_up_share": round(runner_up_share, 1),
                "margin_pct": round(margin_pct, 1),
            }
        )

    out = pd.DataFrame(rows)

    return out.sort_values(["district", "subdistrict"]).reset_index(drop=True)


def build_overall_summary_stats(
    area_stats: pd.DataFrame,
    advance_stats: pd.DataFrame,
) -> pd.DataFrame:
    summary_parts = []

    if not area_stats.empty:
        normal_part = area_stats[
            [
                "area_key",
                "district",
                "subdistrict",
                "winner_party",
                "winner_votes",
                "total_votes",
                "winner_share",
            ]
        ].copy()

        normal_part["summary_type"] = "subdistrict"
        summary_parts.append(normal_part)

    if not advance_stats.empty:
        adv = advance_stats.copy()

        adv["total_votes"] = pd.to_numeric(
            adv["total_votes_in_file"],
            errors="coerce",
        ).fillna(0)

        adv["winner_votes"] = pd.to_numeric(
            adv["winner_votes"],
            errors="coerce",
        ).fillna(0)

        adv["winner_share"] = np.where(
            adv["total_votes"] > 0,
            adv["winner_votes"] / adv["total_votes"] * 100,
            0,
        )

        adv_part = pd.DataFrame(
            {
                "area_key": "advance_set_" + adv["set_no_clean"].astype(str),
                "district": "ล่วงหน้านอกเขต / นอกราชอาณาจักร",
                "subdistrict": "ชุด " + adv["set_no_clean"].astype(str),
                "winner_party": adv["winner_party"].astype(str),
                "winner_votes": adv["winner_votes"],
                "total_votes": adv["total_votes"],
                "winner_share": adv["winner_share"].round(1),
                "summary_type": "advance",
            }
        )

        summary_parts.append(adv_part)

    if not summary_parts:
        return pd.DataFrame()

    return pd.concat(summary_parts, ignore_index=True)


def build_party_unit_wins_by_subdistrict(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "district",
                "subdistrict",
                "winner_party",
                "won_units",
                "total_winner_votes",
                "total_votes_in_file",
            ]
        )

    work = df.copy()

    work["winner_votes"] = pd.to_numeric(
        work["winner_votes"],
        errors="coerce",
    ).fillna(0)

    work["total_votes_in_file"] = pd.to_numeric(
        work["total_votes_in_file"],
        errors="coerce",
    ).fillna(0)

    out = (
        work.groupby(
            ["district", "subdistrict", "winner_party"],
            dropna=False,
            as_index=False,
        )
        .agg(
            won_units=("unit_index", "count"),
            total_winner_votes=("winner_votes", "sum"),
            total_votes_in_file=("total_votes_in_file", "sum"),
        )
        .sort_values(
            ["district", "subdistrict", "won_units", "total_winner_votes"],
            ascending=[True, True, False, False],
        )
        .reset_index(drop=True)
    )

    return out


def build_year_area_stats(year: int) -> pd.DataFrame:
    year_df = apply_dashboard_filters(
        source_df=data,
        year=year,
        election_type=selected_type,
        unit_type=selected_unit_type,
        district=selected_district,
        subdistrict=selected_subdistrict,
        search=search_text,
    )

    year_area_df = year_df[
        (~is_advance_unit_series(year_df["unit_type"]))
        & year_df["subdistrict"].fillna("").astype(str).str.strip().ne("")
    ].copy()

    return build_party_votes_by_area(year_area_df)


def get_compare_status(row: pd.Series) -> str:
    p66 = row.get("winner_party_66")
    p69 = row.get("winner_party_69")

    has66 = pd.notna(p66) and str(p66).strip() not in ["", "nan", "None"]
    has69 = pd.notna(p69) and str(p69).strip() not in ["", "nan", "None"]

    if has66 and has69:
        return "สีเดิม" if party_compare_key(p66) == party_compare_key(p69) else "เปลี่ยนสี"
    if has66 and not has69:
        return "มีเฉพาะปี 66"
    if has69 and not has66:
        return "มีเฉพาะปี 69"

    return "ไม่มีข้อมูล"


def build_comparison_stats(
    stats_66: pd.DataFrame,
    stats_69: pd.DataFrame,
) -> pd.DataFrame:
    cols = [
        "area_key",
        "district",
        "subdistrict",
        "winner_party",
        "winner_votes",
        "runner_up_party",
        "runner_up_votes",
        "margin_pct",
        "total_votes",
        "winner_share",
    ]

    left = stats_66[cols].copy() if not stats_66.empty else pd.DataFrame(columns=cols)
    right = stats_69[cols].copy() if not stats_69.empty else pd.DataFrame(columns=cols)

    left = left.rename(
        columns={
            "district": "district_66",
            "subdistrict": "subdistrict_66",
            "winner_party": "winner_party_66",
            "winner_votes": "winner_votes_66",
            "runner_up_party": "runner_up_party_66",
            "runner_up_votes": "runner_up_votes_66",
            "margin_pct": "margin_pct_66",
            "total_votes": "total_votes_66",
            "winner_share": "winner_share_66",
        }
    )

    right = right.rename(
        columns={
            "district": "district_69",
            "subdistrict": "subdistrict_69",
            "winner_party": "winner_party_69",
            "winner_votes": "winner_votes_69",
            "runner_up_party": "runner_up_party_69",
            "runner_up_votes": "runner_up_votes_69",
            "margin_pct": "margin_pct_69",
            "total_votes": "total_votes_69",
            "winner_share": "winner_share_69",
        }
    )

    merged = left.merge(right, on="area_key", how="outer")

    merged["district"] = merged["district_69"].combine_first(merged["district_66"])
    merged["subdistrict"] = merged["subdistrict_69"].combine_first(
        merged["subdistrict_66"]
    )

    merged["compare_status"] = merged.apply(get_compare_status, axis=1)

    return merged.sort_values(
        ["compare_status", "district", "subdistrict"]
    ).reset_index(drop=True)


def add_race_category(area_stats: pd.DataFrame) -> pd.DataFrame:
    out = area_stats.copy()

    out["race_category"] = np.select(
        [
            out["margin_pct"] <= CLOSE_RACE_THRESHOLD_PCT,
            out["margin_pct"] >= LANDSLIDE_THRESHOLD_PCT,
        ],
        [
            "แข่งขันดุ",
            "ชนะขาด",
        ],
        default="ทั่วไป",
    )

    return out


def build_display_stats(
    area_stats: pd.DataFrame,
    comparison_stats: pd.DataFrame,
    display_mode: str,
    opacity: int,
) -> pd.DataFrame:
    display = area_stats.copy()

    display["display_fill_color"] = display["winner_party"].apply(
        lambda p: get_party_color(p, opacity)
    )
    display["display_line_color"] = [[255, 255, 255, 230] for _ in range(len(display))]
    display["display_note"] = "แสดงตามปีที่เลือก"

    empty_compare_defaults = {
        "compare_status": "-",
        "winner_party_66": "-",
        "winner_party_69": "-",
        "winner_votes_66": 0,
        "winner_votes_69": 0,
        "total_votes_66": 0,
        "total_votes_69": 0,
        "margin_pct_66": 0,
        "margin_pct_69": 0,
    }

    if display_mode == "แสดงตามปีที่เลือก":
        for col, val in empty_compare_defaults.items():
            display[col] = val
        return display

    if display_mode in [
        "แสดงตำบลสีเดิม",
        "แสดงตำบลเปลี่ยนสี",
    ]:
        comp_cols = [
            "area_key",
            "compare_status",
            "winner_party_66",
            "winner_party_69",
            "winner_votes_66",
            "winner_votes_69",
            "total_votes_66",
            "total_votes_69",
            "margin_pct_66",
            "margin_pct_69",
        ]

        comp = comparison_stats[comp_cols].copy()
        display = display.merge(comp, on="area_key", how="left")

        for col, val in empty_compare_defaults.items():
            if col in display.columns:
                display[col] = display[col].fillna(val)
            else:
                display[col] = val

        if display_mode == "แสดงตำบลสีเดิม":
            mask = display["compare_status"] == "สีเดิม"

            display["display_fill_color"] = [
                get_party_color(p, opacity) if ok else GREY_COLOR
                for p, ok in zip(display["winner_party"], mask)
            ]
            display["display_line_color"] = [
                [255, 255, 255, 230] if ok else GREY_LINE_COLOR
                for ok in mask
            ]
            display["display_note"] = [
                "สีเดิม" if ok else "ไม่เข้าเงื่อนไข"
                for ok in mask
            ]

            return display

        mask = display["compare_status"] == "เปลี่ยนสี"

        display["display_fill_color"] = [
            get_party_color(p69, opacity) if ok else GREY_COLOR
            for p69, ok in zip(display["winner_party_69"], mask)
        ]

        display["display_line_color"] = [
            get_party_color(p66, 255) if ok else GREY_LINE_COLOR
            for p66, ok in zip(display["winner_party_66"], mask)
        ]

        display["display_note"] = [
            "เปลี่ยนสี: พื้นที่=ปี69, เส้นขอบ=ปี66"
            if ok
            else "ไม่เข้าเงื่อนไข"
            for ok in mask
        ]

        return display

    for col, val in empty_compare_defaults.items():
        display[col] = val

    if display_mode == "แข่งขันดุ":
        mask = display["margin_pct"] <= CLOSE_RACE_THRESHOLD_PCT

        display["display_fill_color"] = [
            get_party_color(p, opacity) if ok else GREY_COLOR
            for p, ok in zip(display["winner_party"], mask)
        ]
        display["display_line_color"] = [
            [255, 255, 255, 230] if ok else GREY_LINE_COLOR
            for ok in mask
        ]
        display["display_note"] = [
            "แข่งขันดุ" if ok else "ไม่เข้าเงื่อนไข"
            for ok in mask
        ]

        return display

    if display_mode == "ชนะขาด":
        mask = display["margin_pct"] >= LANDSLIDE_THRESHOLD_PCT

        display["display_fill_color"] = [
            get_party_color(p, opacity) if ok else GREY_COLOR
            for p, ok in zip(display["winner_party"], mask)
        ]
        display["display_line_color"] = [
            [255, 255, 255, 230] if ok else GREY_LINE_COLOR
            for ok in mask
        ]
        display["display_note"] = [
            "ชนะขาด" if ok else "ไม่เข้าเงื่อนไข"
            for ok in mask
        ]

        return display

    return display


area_filtered_data = filtered_data[
    (~is_advance_unit_series(filtered_data["unit_type"]))
    & filtered_data["subdistrict"].fillna("").astype(str).str.strip().ne("")
].copy()

area_stats = build_party_votes_by_area(area_filtered_data)

if area_stats.empty:
    st.warning("ไม่สามารถรวมคะแนนตามตำบลได้")
    st.stop()

area_stats = add_race_category(area_stats)

area_stats_66 = build_year_area_stats(2566)
area_stats_69 = build_year_area_stats(2569)

comparison_stats = build_comparison_stats(area_stats_66, area_stats_69)

display_stats = build_display_stats(
    area_stats=area_stats,
    comparison_stats=comparison_stats,
    display_mode=display_mode,
    opacity=fill_opacity,
)

area_stats_dict = area_stats.set_index("area_key").to_dict(orient="index")
display_stats_dict = display_stats.set_index("area_key").to_dict(orient="index")

close_race_stats = area_stats[
    area_stats["margin_pct"] <= CLOSE_RACE_THRESHOLD_PCT
].copy()

landslide_stats = area_stats[
    area_stats["margin_pct"] >= LANDSLIDE_THRESHOLD_PCT
].copy()

year_filtered_for_advance = data[data["year"] == selected_year].copy()
advance_stats = build_advance_set_stats(year_filtered_for_advance, selected_type)

advance_hex_data = build_advance_hex_layer_data(
    advance_stats,
    opacity=fill_opacity,
)

overall_summary_stats = build_overall_summary_stats(
    area_stats=area_stats,
    advance_stats=advance_stats,
)

party_unit_wins_by_subdistrict = build_party_unit_wins_by_subdistrict(
    area_filtered_data
)


# =========================================================
# GEOJSON BUILDER
# =========================================================
def build_choropleth_geojson(
    geojson: dict,
    stats_dict: dict,
    opacity: int = 180,
) -> dict:
    out_geojson = deepcopy(geojson)

    district_candidates = [
        "adm2_name1",
        "adm2_name",
        "ADM2_TH",
        "AMPHOE_T",
        "AMPHOE_TH",
        "district",
        "amphoe",
        "amp_name",
        "อำเภอ",
        "เขต",
    ]

    subdistrict_candidates = [
        "adm3_name1",
        "adm3_name",
        "ADM3_TH",
        "TAMBON_T",
        "TAMBON_TH",
        "subdistrict",
        "tambon",
        "tam_name",
        "ตำบล",
        "แขวง",
    ]

    for feature in out_geojson.get("features", []):
        props = feature.get("properties", {})

        geo_district = extract_feature_property(
            props,
            district_candidates,
        )

        geo_subdistrict = canonical_subdistrict(
            extract_feature_property(
                props,
                subdistrict_candidates,
            )
        )

        area_key = make_area_key(geo_district, geo_subdistrict)
        stat = stats_dict.get(area_key)

        props["geo_district"] = geo_district
        props["geo_subdistrict"] = geo_subdistrict
        props["area_key"] = area_key

        if stat is None:
            props["has_data"] = False
            props["winner_party"] = "ไม่มีข้อมูล"
            props["winner_votes"] = 0
            props["runner_up_party"] = "-"
            props["runner_up_votes"] = 0
            props["margin_votes"] = 0
            props["margin_pct"] = 0
            props["total_votes"] = 0
            props["winner_share"] = 0
            props["compare_status"] = "ไม่มีข้อมูล"
            props["winner_party_66"] = "-"
            props["winner_party_69"] = "-"
            props["winner_votes_66"] = 0
            props["winner_votes_69"] = 0
            props["total_votes_66"] = 0
            props["total_votes_69"] = 0
            props["display_note"] = "ไม่มีข้อมูล"
            props["fill_color"] = NO_DATA_COLOR
            props["line_color"] = GREY_LINE_COLOR
        else:
            props["has_data"] = True
            props["winner_party"] = stat["winner_party"]
            props["winner_votes"] = int(stat["winner_votes"])
            props["runner_up_party"] = stat.get("runner_up_party", "-")
            props["runner_up_votes"] = int(stat.get("runner_up_votes", 0))
            props["margin_votes"] = int(stat.get("margin_votes", 0))
            props["margin_pct"] = float(stat.get("margin_pct", 0))
            props["total_votes"] = int(stat["total_votes"])
            props["winner_share"] = float(stat["winner_share"])

            props["compare_status"] = stat.get("compare_status", "-")
            props["winner_party_66"] = stat.get("winner_party_66", "-")
            props["winner_party_69"] = stat.get("winner_party_69", "-")
            props["winner_votes_66"] = safe_int(stat.get("winner_votes_66", 0))
            props["winner_votes_69"] = safe_int(stat.get("winner_votes_69", 0))
            props["total_votes_66"] = safe_int(stat.get("total_votes_66", 0))
            props["total_votes_69"] = safe_int(stat.get("total_votes_69", 0))
            props["margin_pct_66"] = safe_float(stat.get("margin_pct_66", 0))
            props["margin_pct_69"] = safe_float(stat.get("margin_pct_69", 0))

            props["display_note"] = stat.get("display_note", "แสดงตามปีที่เลือก")
            props["fill_color"] = stat.get(
                "display_fill_color",
                get_party_color(stat["winner_party"], opacity),
            )
            props["line_color"] = stat.get(
                "display_line_color",
                [255, 255, 255, 230],
            )

        feature["properties"] = props

    return out_geojson


choropleth_geojson = build_choropleth_geojson(
    base_geojson,
    display_stats_dict,
    opacity=fill_opacity,
)


# =========================================================
# MAP CENTER
# =========================================================
def get_geojson_center(geojson: dict) -> tuple[float, float]:
    lats = []
    lons = []

    for feature in geojson.get("features", []):
        props = feature.get("properties", {})

        lat = pd.to_numeric(props.get("center_lat"), errors="coerce")
        lon = pd.to_numeric(props.get("center_lon"), errors="coerce")

        if pd.notna(lat) and pd.notna(lon):
            lats.append(float(lat))
            lons.append(float(lon))

    if lats and lons:
        return float(np.mean(lats)), float(np.mean(lons))

    return 18.75, 99.00


map_lat, map_lon = get_geojson_center(base_geojson)


# =========================================================
# KEY METRICS
# =========================================================
if overall_summary_stats.empty:
    st.warning("ไม่มีข้อมูลสำหรับสรุป KPI")
    st.stop()

top_party = overall_summary_stats["winner_party"].value_counts().idxmax()
total_votes = overall_summary_stats["total_votes"].sum()

normal_area_count = area_stats["area_key"].nunique()
advance_area_count = len(advance_stats)
covered_area_count = normal_area_count + advance_area_count

geo_features = choropleth_geojson.get("features", [])

matched_features = sum(
    1
    for f in geo_features
    if f.get("properties", {}).get("has_data") is True
)

same_color_count = (
    int((comparison_stats["compare_status"] == "สีเดิม").sum())
    if not comparison_stats.empty
    else 0
)

changed_color_count = (
    int((comparison_stats["compare_status"] == "เปลี่ยนสี").sum())
    if not comparison_stats.empty
    else 0
)

close_race_count = len(close_race_stats)
landslide_count = len(landslide_stats)

m1, m2, m3, m4 = st.columns(4)

with m1:
    st.metric("พรรคที่ชนะมากสุด", top_party)

with m2:
    st.metric("Total Votes", format_int(total_votes))

with m3:
    st.metric(
        "พื้นที่/ชุดที่มีข้อมูลคะแนน",
        f"{covered_area_count:,}",
        help=f"ตำบลปกติ {normal_area_count:,} + ล่วงหน้านอกเขต {advance_area_count:,} ชุด",
    )

with m4:
    st.metric("GeoJSON Match", f"{matched_features:,}/{len(geo_features):,}")

m5, m6, m7, m8 = st.columns(4)

with m5:
    st.metric("สีเดิม 66 → 69", f"{same_color_count:,}")

with m6:
    st.metric("เปลี่ยนสี 66 → 69", f"{changed_color_count:,}")

with m7:
    st.metric("แข่งขันดุ ≤ 5%", f"{close_race_count:,}")

with m8:
    st.metric("ชนะขาด ≥ 15%", f"{landslide_count:,}")


# =========================================================
# MAP LAYERS
# =========================================================
def render_pydeck_map(
    geojson_data: dict,
    tooltip: dict,
    key: str,
    height: int = 680,
) -> None:
    geojson_layer = pdk.Layer(
        "GeoJsonLayer",
        data=geojson_data,
        id=key,
        pickable=True,
        stroked=True,
        filled=True,
        extruded=False,
        get_fill_color="properties.fill_color",
        get_line_color="properties.line_color",
        line_width_min_pixels=line_width,
        auto_highlight=True,
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[geojson_layer],
            initial_view_state=pdk.ViewState(
                latitude=map_lat,
                longitude=map_lon,
                zoom=8.4,
                pitch=0,
            ),
            map_style=MAP_STYLES[map_style],
            tooltip=tooltip,
        ),
        height=height,
        use_container_width=True,
    )


winner_tooltip = {
    "html": """
    <b>อำเภอ:</b> {geo_district}<br/>
    <b>ตำบล:</b> {geo_subdistrict}<br/>
    ──────────────<br/>
    <b>Mode:</b> {display_note}<br/>
    <b>Winner:</b> {winner_party}<br/>
    <b>Winner votes:</b> {winner_votes}<br/>
    <b>Runner-up:</b> {runner_up_party} ({runner_up_votes})<br/>
    <b>Margin:</b> {margin_votes} votes ({margin_pct}%)<br/>
    <b>Total votes:</b> {total_votes}<br/>
    <b>Winner share:</b> {winner_share}%<br/>
    ──────────────<br/>
    <b>ปี 66:</b> {winner_party_66} ({winner_votes_66})<br/>
    <b>ปี 69:</b> {winner_party_69} ({winner_votes_69})<br/>
    """,
    "style": {
        "backgroundColor": "black",
        "color": "white",
        "fontFamily": "sans-serif",
        "fontSize": "13px",
        "padding": "10px",
    },
}



# =========================================================
# CONSTITUENCY VS PARTY LIST FUNCTIONS
# =========================================================
def normalize_election_type_key(value: Any) -> str:
    text = str(value).strip().lower()

    if (
        text == "partylist"
        or "party" in text
        or "list" in text
        or "บัญชี" in text
        or "บช" in text
    ):
        return "partylist"

    return "constituency"


def election_type_display(value: Any) -> str:
    key = normalize_election_type_key(value)
    if key == "partylist":
        return "บชรายชื่อ"
    return "สส เขต"


def direction_from_diff(value: float) -> str:
    if pd.isna(value):
        return "ไม่มีข้อมูล"
    if value > 0:
        return "เลือกคนมากกว่าพรรค"
    if value < 0:
        return "เลือกพรรคมากกว่าคน"
    return "เท่ากัน"


def trend_direction_from_delta(value: float) -> str:
    if pd.isna(value):
        return "ไม่มีข้อมูล"
    if value > 0:
        return "เพิ่มขึ้น"
    if value < 0:
        return "ลดลง"
    return "ทรงตัว"


def clean_subdistrict_for_vote(value: Any) -> str:
    return canonical_subdistrict(value)


def make_vote_unit_key(row: pd.Series) -> str:
    """Create a stable key to match constituency and party-list rows at polling-unit level."""
    district = normalize_district(row.get("district_norm", row.get("district", "")))
    subdistrict = clean_subdistrict_for_vote(row.get("subdistrict_norm", row.get("subdistrict", "")))
    village_no = clean_id(row.get("village_no", ""))
    precinct_no = clean_id(row.get("precinct_no", ""))
    set_no = clean_id(row.get("set_no", ""))

    if precinct_no:
        unit_part = f"precinct_{precinct_no}"
    elif set_no:
        unit_part = f"set_{set_no}"
    else:
        unit_part = normalize_text(row.get("unit_index", ""))

    return "__".join(
        [
            normalize_text(district),
            normalize_text(subdistrict),
            f"village_{village_no}",
            unit_part,
        ]
    )


def make_vote_unit_label(row: pd.Series) -> str:
    village_no = clean_id(row.get("village_no", ""))
    precinct_no = clean_id(row.get("precinct_no", ""))
    set_no = clean_id(row.get("set_no", ""))

    parts = []

    if village_no:
        parts.append(f"หมู่ {village_no}")

    if precinct_no:
        parts.append(f"หน่วย {precinct_no}")
    elif set_no:
        parts.append(f"ชุด {set_no}")
    else:
        unit_index = str(row.get("unit_index", "")).strip()
        if unit_index:
            parts.append(unit_index)

    return " / ".join(parts) if parts else "ไม่ทราบหน่วย"


def build_party_votes_by_ballot_type(
    source_df: pd.DataFrame,
    selected_years: list[int] | None = None,
    selected_districts: list[str] | None = None,
    selected_subdistricts: list[str] | None = None,
    include_advance: bool = False,
) -> pd.DataFrame:
    """Explode results into party votes by ballot type.

    This version keeps polling-unit identifiers so Insight scatter can use
    1 point = 1 polling unit in each subdistrict.
    """
    work = source_df.copy()

    work["election_type_key"] = work["election_type"].apply(normalize_election_type_key)
    work["ballot_type"] = work["election_type"].apply(election_type_display)
    work["district_norm"] = work["district"].apply(normalize_district)
    work["subdistrict_norm"] = work["subdistrict"].apply(clean_subdistrict_for_vote)

    # Fix rows where party-list data stores district as "เขต 7".
    # Use subdistrict -> real district lookup from rows that already have real district names.
    ref = work[
        work["district_norm"].isin(DISTRICT_ORDER)
        & work["subdistrict_norm"].fillna("").astype(str).str.strip().ne("")
    ].copy()
    if not ref.empty:
        subdistrict_to_district = (
            ref.groupby("subdistrict_norm")["district_norm"]
            .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
            .to_dict()
        )
        infer_mask = (
            ~work["district_norm"].isin(DISTRICT_ORDER)
            & work["subdistrict_norm"].isin(subdistrict_to_district.keys())
        )
        work.loc[infer_mask, "district_norm"] = work.loc[infer_mask, "subdistrict_norm"].map(subdistrict_to_district)

    if selected_years:
        work = work[work["year"].astype(int).isin(selected_years)].copy()

    if selected_districts:
        work = work[work["district_norm"].isin(selected_districts)].copy()

    if selected_subdistricts:
        work = work[work["subdistrict_norm"].isin(selected_subdistricts)].copy()

    if not include_advance:
        work = work[~is_advance_unit_series(work["unit_type"])].copy()
        # Exclude residual "เขต 7" / unknown area rows from normal polling-unit statistics.
        work = work[work["district_norm"].isin(DISTRICT_ORDER)].copy()

    work = work[work["subdistrict_norm"].fillna("").astype(str).str.strip().ne("")].copy()

    records = []

    for _, row in work.iterrows():
        year = int(row["year"])
        election_type_key = row["election_type_key"]
        ballot_type = row["ballot_type"]
        district = row["district_norm"]
        subdistrict = row["subdistrict_norm"]
        unit_type = str(row.get("unit_type", "")).strip()
        village_no = clean_id(row.get("village_no", ""))
        precinct_no = clean_id(row.get("precinct_no", ""))
        set_no = clean_id(row.get("set_no", ""))
        unit_key = make_vote_unit_key(row)
        unit_label = make_vote_unit_label(row)

        result_table = normalize_results_table(row.get("results", []))

        if not result_table.empty and "party_name" in result_table.columns:
            for _, r in result_table.iterrows():
                party = canonical_party(r.get("party_name", ""))
                votes = pd.to_numeric(r.get("votes", 0), errors="coerce")

                if party == "" or pd.isna(votes):
                    continue

                records.append(
                    {
                        "year": year,
                        "election_type_key": election_type_key,
                        "ballot_type": ballot_type,
                        "district": district,
                        "subdistrict": subdistrict,
                        "unit_type": unit_type,
                        "unit_key": unit_key,
                        "unit_label": unit_label,
                        "village_no": village_no,
                        "precinct_no": precinct_no,
                        "set_no": set_no,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )
        else:
            party = canonical_party(row.get("winner_party", ""))
            votes = pd.to_numeric(row.get("winner_votes", 0), errors="coerce")

            if party != "" and not pd.isna(votes):
                records.append(
                    {
                        "year": year,
                        "election_type_key": election_type_key,
                        "ballot_type": ballot_type,
                        "district": district,
                        "subdistrict": subdistrict,
                        "unit_type": unit_type,
                        "unit_key": unit_key,
                        "unit_label": unit_label,
                        "village_no": village_no,
                        "precinct_no": precinct_no,
                        "set_no": set_no,
                        "party": party,
                        "party_compare_key": party_compare_key(party),
                        "party_compare_label": party_compare_label(party),
                        "votes": float(votes),
                    }
                )

    if not records:
        return pd.DataFrame(
            columns=[
                "year", "election_type_key", "ballot_type", "district", "subdistrict",
                "unit_key", "unit_label", "village_no", "precinct_no", "set_no", "party", "party_compare_key", "party_compare_label", "party_compare_key", "party_compare_label", "votes",
            ]
        )

    vote_df = pd.DataFrame(records)

    out = (
        vote_df.groupby(
            [
                "year", "election_type_key", "ballot_type", "district", "subdistrict",
                "unit_key", "unit_label", "village_no", "precinct_no", "set_no", "party", "party_compare_key", "party_compare_label",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(votes=("votes", "sum"))
    )

    out["votes"] = out["votes"].round(0).astype(int)

    return out


def aggregate_vote_split_by_scope(vote_df: pd.DataFrame, scope: str) -> pd.DataFrame:
    if vote_df.empty:
        return vote_df.copy()

    if scope == "รายหน่วย":
        group_cols = [
            "year", "district", "subdistrict", "unit_key", "unit_label",
            "village_no", "precinct_no", "set_no", "party", "party_compare_key", "party_compare_label", "election_type_key", "ballot_type",
        ]
    elif scope == "รายตำบล":
        group_cols = ["year", "district", "subdistrict", "party", "party_compare_key", "party_compare_label", "election_type_key", "ballot_type"]
    elif scope == "รายอำเภอ":
        group_cols = ["year", "district", "party", "party_compare_key", "party_compare_label", "election_type_key", "ballot_type"]
    else:
        group_cols = ["year", "party", "party_compare_key", "party_compare_label", "election_type_key", "ballot_type"]

    out = (
        vote_df.groupby(group_cols, as_index=False, dropna=False)
        .agg(votes=("votes", "sum"))
        .sort_values(["year", "party", "ballot_type"])
    )

    return out


def build_constituency_partylist_comparison(
    aggregated_votes: pd.DataFrame,
    scope: str,
) -> pd.DataFrame:
    if aggregated_votes.empty:
        return pd.DataFrame()

    if scope == "รายหน่วย":
        index_cols = [
            "year", "district", "subdistrict", "unit_key", "unit_label",
            "village_no", "precinct_no", "set_no", "party", "party_compare_key", "party_compare_label",
        ]
    elif scope == "รายตำบล":
        index_cols = ["year", "district", "subdistrict", "party", "party_compare_key", "party_compare_label"]
    elif scope == "รายอำเภอ":
        index_cols = ["year", "district", "party", "party_compare_key", "party_compare_label"]
    else:
        index_cols = ["year", "party", "party_compare_key", "party_compare_label"]

    wide = (
        aggregated_votes.pivot_table(
            index=index_cols,
            columns="election_type_key",
            values="votes",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
        .rename_axis(None, axis=1)
    )

    for col in ["constituency", "partylist"]:
        if col not in wide.columns:
            wide[col] = 0

    wide = wide.rename(
        columns={
            "constituency": "constituency_votes",
            "partylist": "partylist_votes",
        }
    )

    wide["total_two_ballots"] = wide["constituency_votes"] + wide["partylist_votes"]
    wide["person_minus_party_votes"] = wide["constituency_votes"] - wide["partylist_votes"]

    wide["person_minus_party_pct_of_partylist"] = np.where(
        wide["partylist_votes"] > 0,
        wide["person_minus_party_votes"] / wide["partylist_votes"] * 100,
        np.nan,
    )

    wide["person_minus_party_pct_of_total"] = np.where(
        wide["total_two_ballots"] > 0,
        wide["person_minus_party_votes"] / wide["total_two_ballots"] * 100,
        np.nan,
    )

    wide["vote_direction"] = wide["person_minus_party_votes"].apply(direction_from_diff)

    numeric_cols = [
        "constituency_votes", "partylist_votes", "total_two_ballots",
        "person_minus_party_votes", "person_minus_party_pct_of_partylist",
        "person_minus_party_pct_of_total",
    ]

    for col in numeric_cols:
        wide[col] = pd.to_numeric(wide[col], errors="coerce")

    wide[["person_minus_party_pct_of_partylist", "person_minus_party_pct_of_total"]] = wide[
        ["person_minus_party_pct_of_partylist", "person_minus_party_pct_of_total"]
    ].round(2)

    return wide.sort_values(
        ["year", "total_two_ballots"],
        ascending=[True, False],
    ).reset_index(drop=True)


def build_vote_trend_summary(comparison_df: pd.DataFrame, scope: str) -> pd.DataFrame:
    if comparison_df.empty:
        return pd.DataFrame()

    if scope == "รายหน่วย":
        index_cols = ["district", "subdistrict", "unit_key", "unit_label", "party_compare_key", "party_compare_label"]
    elif scope == "รายตำบล":
        index_cols = ["district", "subdistrict", "party_compare_key", "party_compare_label"]
    elif scope == "รายอำเภอ":
        index_cols = ["district", "party_compare_key", "party_compare_label"]
    else:
        index_cols = ["party_compare_key", "party_compare_label"]

    rows = []

    for keys, group in comparison_df.groupby(index_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)

        key_dict = dict(zip(index_cols, keys))

        g66 = group[group["year"] == 2566]
        g69 = group[group["year"] == 2569]

        row66 = g66.iloc[0] if not g66.empty else None
        row69 = g69.iloc[0] if not g69.empty else None

        constituency_66 = row66["constituency_votes"] if row66 is not None else np.nan
        partylist_66 = row66["partylist_votes"] if row66 is not None else np.nan
        gap_66 = row66["person_minus_party_votes"] if row66 is not None else np.nan

        constituency_69 = row69["constituency_votes"] if row69 is not None else np.nan
        partylist_69 = row69["partylist_votes"] if row69 is not None else np.nan
        gap_69 = row69["person_minus_party_votes"] if row69 is not None else np.nan
        party_66 = row66["party"] if row66 is not None and "party" in row66.index else np.nan
        party_69 = row69["party"] if row69 is not None and "party" in row69.index else np.nan

        constituency_delta = (
            constituency_69 - constituency_66
            if pd.notna(constituency_66) and pd.notna(constituency_69)
            else np.nan
        )

        partylist_delta = (
            partylist_69 - partylist_66
            if pd.notna(partylist_66) and pd.notna(partylist_69)
            else np.nan
        )

        gap_delta = (
            gap_69 - gap_66
            if pd.notna(gap_66) and pd.notna(gap_69)
            else np.nan
        )

        sign_candidate = np.sign(constituency_delta) if pd.notna(constituency_delta) else np.nan
        sign_party = np.sign(partylist_delta) if pd.notna(partylist_delta) else np.nan

        if pd.isna(sign_candidate) or pd.isna(sign_party):
            trend_alignment = "ข้อมูลไม่ครบ 2 ปี"
        elif sign_candidate == 0 and sign_party == 0:
            trend_alignment = "ทรงตัวทั้งคู่"
        elif sign_candidate == sign_party or sign_candidate == 0 or sign_party == 0:
            trend_alignment = "ไปทิศทางเดียวกัน"
        else:
            trend_alignment = "ไปคนละทาง"

        if pd.isna(gap_66) or pd.isna(gap_69):
            gap_change_type = "ข้อมูลไม่ครบ 2 ปี"
        elif gap_66 > 0 and gap_69 > 0:
            gap_change_type = "เลือกคนมากกว่าพรรคทั้ง 2 ปี"
        elif gap_66 < 0 and gap_69 < 0:
            gap_change_type = "เลือกพรรคมากกว่าคนทั้ง 2 ปี"
        elif gap_66 > 0 and gap_69 < 0:
            gap_change_type = "66 เลือกคนมากกว่า → 69 เลือกพรรคมากกว่า"
        elif gap_66 < 0 and gap_69 > 0:
            gap_change_type = "66 เลือกพรรคมากกว่า → 69 เลือกคนมากกว่า"
        else:
            gap_change_type = "มีปีที่คะแนนเท่ากัน"

        rows.append(
            {
                **key_dict,
                "party": key_dict.get("party_compare_label", key_dict.get("party", "")),
                "party_66": party_66,
                "party_69": party_69,
                "constituency_votes_66": constituency_66,
                "partylist_votes_66": partylist_66,
                "person_minus_party_votes_66": gap_66,
                "direction_66": direction_from_diff(gap_66),
                "constituency_votes_69": constituency_69,
                "partylist_votes_69": partylist_69,
                "person_minus_party_votes_69": gap_69,
                "direction_69": direction_from_diff(gap_69),
                "constituency_delta_69_minus_66": constituency_delta,
                "partylist_delta_69_minus_66": partylist_delta,
                "gap_delta_69_minus_66": gap_delta,
                "constituency_trend": trend_direction_from_delta(constituency_delta),
                "partylist_trend": trend_direction_from_delta(partylist_delta),
                "trend_alignment": trend_alignment,
                "gap_change_type": gap_change_type,
            }
        )

    out = pd.DataFrame(rows)

    numeric_cols = [
        "constituency_votes_66",
        "partylist_votes_66",
        "person_minus_party_votes_66",
        "constituency_votes_69",
        "partylist_votes_69",
        "person_minus_party_votes_69",
        "constituency_delta_69_minus_66",
        "partylist_delta_69_minus_66",
        "gap_delta_69_minus_66",
    ]

    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    sort_cols = [c for c in ["gap_change_type", "party", "district", "subdistrict"] if c in out.columns]

    return out.sort_values(sort_cols).reset_index(drop=True)


def render_subdistrict_trend_scatter(
    df: pd.DataFrame,
    party: str,
    year: int,
    show_district_trend: bool = True,
) -> go.Figure:
    """Scatter: x=party-list votes, y=constituency votes, each point=polling unit."""
    plot_df = df[
        (df.get("party_compare_label", df["party"]) == party)
        & (df["year"] == year)
        & (df["total_two_ballots"] > 0)
    ].copy()

    fig = go.Figure()

    if plot_df.empty:
        fig.update_layout(
            title=f"{party} ปี {year}: ไม่มีข้อมูลรายหน่วย",
            height=520,
        )
        return fig

    districts = sorted(plot_df["district"].dropna().astype(str).unique().tolist())

    palette = px.colors.qualitative.Plotly
    color_map = {d: palette[i % len(palette)] for i, d in enumerate(districts)}

    for district_name in districts:
        g = plot_df[plot_df["district"] == district_name].copy()

        fig.add_trace(
            go.Scatter(
                x=g["partylist_votes"],
                y=g["constituency_votes"],
                mode="markers",
                name=district_name,
                marker=dict(
                    size=8,
                    color=color_map[district_name],
                    opacity=0.75,
                ),
                customdata=np.stack(
                    [
                        g["subdistrict"].astype(str),
                        g.get("unit_label", pd.Series([""] * len(g), index=g.index)).astype(str),
                        g["person_minus_party_votes"],
                        g["vote_direction"].astype(str),
                    ],
                    axis=-1,
                ),
                hovertemplate=(
                    "<b>ตำบล:</b> %{customdata[0]}<br>"
                    "<b>หน่วย:</b> %{customdata[1]}<br>"
                    "<b>บชรายชื่อ:</b> %{x:,.0f}<br>"
                    "<b>สส เขต:</b> %{y:,.0f}<br>"
                    "<b>เขต - บช:</b> %{customdata[2]:,.0f}<br>"
                    "<b>ตีความ:</b> %{customdata[3]}<br>"
                    "<extra></extra>"
                ),
            )
        )

        if show_district_trend:
            gg = g[["partylist_votes", "constituency_votes"]].dropna()
            gg = gg[gg["partylist_votes"] > 0]

            if len(gg) >= 2 and gg["partylist_votes"].nunique() >= 2:
                x = gg["partylist_votes"].astype(float).to_numpy()
                y = gg["constituency_votes"].astype(float).to_numpy()

                slope, intercept = np.polyfit(x, y, 1)
                xs = np.linspace(x.min(), x.max(), 50)
                ys = slope * xs + intercept

                fig.add_trace(
                    go.Scatter(
                        x=xs,
                        y=ys,
                        mode="lines",
                        name=f"แนวโน้ม {district_name}",
                        line=dict(
                            color=color_map[district_name],
                            width=2,
                        ),
                        hoverinfo="skip",
                        showlegend=False,
                    )
                )

    # เส้น y=x ใช้ดูว่า สส เขต เท่ากับ บชรายชื่อ หรือไม่
    max_axis = max(
        float(plot_df["partylist_votes"].max()),
        float(plot_df["constituency_votes"].max()),
    )

    fig.add_trace(
        go.Scatter(
            x=[0, max_axis],
            y=[0, max_axis],
            mode="lines",
            name="เส้นเท่ากัน",
            line=dict(color="gray", width=1.5, dash="dash"),
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        title=f"{party} ปี {year}: แนวโน้มรายหน่วยของ สส เขต เทียบกับ บชรายชื่อ",
        height=560,
        xaxis_title="คะแนน บชรายชื่อ รายหน่วย",
        yaxis_title="คะแนน สส เขต รายหน่วย",
        legend_title_text="อำเภอ",
    )

    fig.update_xaxes(rangemode="tozero")
    fig.update_yaxes(rangemode="tozero")

    return fig

# =========================================================
# TABS
# =========================================================
map_tab, ranking_tab, detail_tab, education_tab, vote_split_tab, insight_tab, raw_tab = st.tabs(
    [
        "Map",
        "Ranking",
        "Subdistrict Detail",
        "Education Level",
        "เขต vs บชรายชื่อ",
        "Statistics Insight",
        "Raw / Debug",
    ]
)


# =========================================================
# MAP TAB
# =========================================================
with map_tab:
    title_col, mode_col = st.columns([3.5, 1.5])

    with title_col:
        st.subheader(f"แผนที่รายตำบล - ปี {selected_year}")
        st.caption(f"โหมดที่เลือก: {display_mode}")

    with mode_col:
        st.selectbox(
            "Display Mode",
            DISPLAY_MODES,
            index=DISPLAY_MODES.index(display_mode),
            key="display_mode",
            label_visibility="collapsed",
        )

    legend_parties = (
        area_stats["winner_party"]
        .dropna()
        .astype(str)
        .value_counts()
        .index
        .tolist()
    )

    legend_html = render_mode_legend(display_mode, legend_parties)

    if legend_html.strip():
        components.html(
            legend_html,
            height=44,
            scrolling=False,
        )

    render_pydeck_map(
        geojson_data=choropleth_geojson,
        tooltip=winner_tooltip,
        key="display_map",
    )

    if display_mode == "แสดงตำบลเปลี่ยนสี":
        st.caption(
            "หมายเหตุ: แผนที่ polygon ไม่สามารถทำลายเฉียงทับกันแบบตัวอย่างได้โดยตรงใน GeoJsonLayer; "
            "โหมดนี้จึงใช้สีพื้นที่เป็นพรรคที่ชนะปี 69 และสีเส้นขอบเป็นพรรคที่ชนะปี 66"
        )
    else:
        st.caption(
            f"สีของแต่ละตำบลแสดงตามโหมดที่เลือก | ปี {selected_year}"
        )

    st.divider()

    if advance_hex_data.empty:
        st.info("ไม่มีข้อมูลล่วงหน้านอกเขต / advance unit สำหรับประเภทบัตรนี้")
    else:
        st.subheader(f"ล่วงหน้านอกเขต / นอกราชอาณาจักร รายชุด - ปี {selected_year}")

        advance_legend_html = render_advance_party_legend(advance_hex_data)

        if advance_legend_html.strip():
            components.html(
                advance_legend_html,
                height=40,
                scrolling=False,
            )

        advance_hex_fig = render_advance_hex_plotly(advance_hex_data)

        st.plotly_chart(
            advance_hex_fig,
            use_container_width=False,
            config={
                "displayModeBar": False,
                "scrollZoom": False,
                "doubleClick": False,
                "showTips": False,
                "responsive": False,
            },
        )


# =========================================================
# RANKING TAB
# =========================================================
with ranking_tab:
    st.subheader(f"จำนวนพื้นที่/ชุดที่แต่ละพรรคชนะ - ปี {selected_year}")

    overall_party_ranking = (
        overall_summary_stats.groupby("winner_party", as_index=False)
        .agg(
            won_areas=("area_key", "count"),
            total_winner_votes=("winner_votes", "sum"),
            total_votes=("total_votes", "sum"),
            avg_winner_share=("winner_share", "mean"),
        )
        .sort_values(
            ["won_areas", "total_winner_votes"],
            ascending=False,
        )
    )

    overall_party_ranking["avg_winner_share"] = (
        overall_party_ranking["avg_winner_share"].round(1)
    )

    st.dataframe(
        overall_party_ranking,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(f"จำนวนตำบลปกติที่แต่ละพรรคชนะ - ปี {selected_year}")

    party_ranking = (
        area_stats.groupby("winner_party", as_index=False)
        .agg(
            won_subdistricts=("area_key", "count"),
            total_winner_votes=("winner_votes", "sum"),
            total_votes=("total_votes", "sum"),
            avg_winner_share=("winner_share", "mean"),
        )
        .sort_values(
            ["won_subdistricts", "total_winner_votes"],
            ascending=False,
        )
    )

    party_ranking["avg_winner_share"] = party_ranking["avg_winner_share"].round(1)

    st.dataframe(
        party_ranking,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(f"จำนวนหน่วยเลือกตั้งที่แต่ละพรรคชนะ แยกตามตำบล - ปี {selected_year}")

    if party_unit_wins_by_subdistrict.empty:
        st.info("ไม่มีข้อมูลจำนวนหน่วยเลือกตั้งที่แต่ละพรรคชนะ")
    else:
        st.dataframe(
            party_unit_wins_by_subdistrict.rename(
                columns={
                    "district": "อำเภอ",
                    "subdistrict": "ตำบล",
                    "winner_party": "พรรคที่ชนะ",
                    "won_units": "จำนวนหน่วยที่ชนะ",
                    "total_winner_votes": "คะแนนผู้ชนะรวม",
                    "total_votes_in_file": "คะแนนรวมทุกหน่วย",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(f"ตำบลที่แข่งขันดุ ≤ 5% - ปี {selected_year}")

    if close_race_stats.empty:
        st.info("ไม่มีตำบลที่เข้าเงื่อนไขแข่งขันดุ")
    else:
        st.dataframe(
            close_race_stats[
                [
                    "district",
                    "subdistrict",
                    "winner_party",
                    "winner_votes",
                    "runner_up_party",
                    "runner_up_votes",
                    "margin_votes",
                    "margin_pct",
                    "total_votes",
                    "winner_share",
                ]
            ]
            .sort_values("margin_pct")
            .rename(
                columns={
                    "district": "อำเภอ",
                    "subdistrict": "ตำบล",
                    "winner_party": "พรรคชนะ",
                    "winner_votes": "คะแนนอันดับ 1",
                    "runner_up_party": "พรรคอันดับ 2",
                    "runner_up_votes": "คะแนนอันดับ 2",
                    "margin_votes": "ส่วนต่างคะแนน",
                    "margin_pct": "ส่วนต่าง %",
                    "total_votes": "คะแนนรวม",
                    "winner_share": "Winner share %",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(f"ตำบลที่ชนะขาด ≥ 15% - ปี {selected_year}")

    if landslide_stats.empty:
        st.info("ไม่มีตำบลที่เข้าเงื่อนไขชนะขาด")
    else:
        st.dataframe(
            landslide_stats[
                [
                    "district",
                    "subdistrict",
                    "winner_party",
                    "winner_votes",
                    "runner_up_party",
                    "runner_up_votes",
                    "margin_votes",
                    "margin_pct",
                    "total_votes",
                    "winner_share",
                ]
            ]
            .sort_values("margin_pct", ascending=False)
            .rename(
                columns={
                    "district": "อำเภอ",
                    "subdistrict": "ตำบล",
                    "winner_party": "พรรคชนะ",
                    "winner_votes": "คะแนนอันดับ 1",
                    "runner_up_party": "พรรคอันดับ 2",
                    "runner_up_votes": "คะแนนอันดับ 2",
                    "margin_votes": "ส่วนต่างคะแนน",
                    "margin_pct": "ส่วนต่าง %",
                    "total_votes": "คะแนนรวม",
                    "winner_share": "Winner share %",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(f"ตำบลที่ผู้ชนะมีคะแนนสูงสุด - ปี {selected_year}")

    top_subdistricts = area_stats.sort_values(
        "winner_votes",
        ascending=False,
    ).head(20)

    st.dataframe(
        top_subdistricts[
            [
                "district",
                "subdistrict",
                "winner_party",
                "winner_votes",
                "runner_up_party",
                "runner_up_votes",
                "margin_votes",
                "margin_pct",
                "total_votes",
                "winner_share",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(f"ล่วงหน้านอกเขต / นอกราชอาณาจักร รายชุด - ปี {selected_year}")

    if advance_stats.empty:
        st.info("ไม่มีข้อมูลล่วงหน้านอกเขต / advance unit สำหรับประเภทบัตรนี้")
    else:
        st.dataframe(
            advance_stats[
                [
                    "unit_type",
                    "set_no_clean",
                    "winner_party",
                    "winner_votes",
                    "runner_up_party",
                    "runner_up_votes",
                    "margin",
                    "total_votes_in_file",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )


# =========================================================
# DETAIL TAB
# =========================================================
with detail_tab:
    st.subheader(f"รายละเอียดคะแนนรายตำบล - ปี {selected_year}")

    selected_area_label = st.selectbox(
        "เลือกตำบล",
        options=(
            area_stats["district"].astype(str)
            + " / "
            + area_stats["subdistrict"].astype(str)
        ).tolist(),
    )

    selected_district_name, selected_subdistrict_name = [
        x.strip()
        for x in selected_area_label.split("/", 1)
    ]

    selected_area_key = make_area_key(
        selected_district_name,
        selected_subdistrict_name,
    )

    selected_rows = area_filtered_data[
        area_filtered_data["area_key"] == selected_area_key
    ].copy()

    if selected_rows.empty:
        st.info("ไม่มีข้อมูลของตำบลนี้")
    else:
        selected_stat = area_stats[
            area_stats["area_key"] == selected_area_key
        ].iloc[0]

        c1, c2, c3, c4, c5 = st.columns(5)

        with c1:
            st.metric("Winner", selected_stat["winner_party"])

        with c2:
            st.metric("Winner Votes", format_int(selected_stat["winner_votes"]))

        with c3:
            st.metric("Runner-up", selected_stat["runner_up_party"])

        with c4:
            st.metric("Margin", f"{selected_stat['margin_pct']:.1f}%")

        with c5:
            st.metric("Total Votes", format_int(selected_stat["total_votes"]))

        st.write(
            f"**พื้นที่:** {selected_stat['district']} / {selected_stat['subdistrict']}"
        )

        st.subheader("จำนวนหน่วยเลือกตั้งที่แต่ละพรรคชนะในตำบลนี้")

        selected_unit_wins = party_unit_wins_by_subdistrict[
            (party_unit_wins_by_subdistrict["district"] == selected_stat["district"])
            & (
                party_unit_wins_by_subdistrict["subdistrict"]
                == selected_stat["subdistrict"]
            )
        ].copy()

        if selected_unit_wins.empty:
            st.info("ไม่มีข้อมูลจำนวนหน่วยที่แต่ละพรรคชนะในตำบลนี้")
        else:
            st.dataframe(
                selected_unit_wins[
                    [
                        "winner_party",
                        "won_units",
                        "total_winner_votes",
                        "total_votes_in_file",
                    ]
                ].rename(
                    columns={
                        "winner_party": "พรรคที่ชนะ",
                        "won_units": "จำนวนหน่วยที่ชนะ",
                        "total_winner_votes": "คะแนนผู้ชนะรวม",
                        "total_votes_in_file": "คะแนนรวมทุกหน่วย",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("คะแนนรวมพรรคในตำบลนี้")

        party_records = []

        for _, row in selected_rows.iterrows():
            result_table = normalize_results_table(row["results"])

            if not result_table.empty:
                for _, r in result_table.iterrows():
                    party = canonical_party(r.get("party_name", ""))
                    votes = pd.to_numeric(r.get("votes", 0), errors="coerce")

                    if party != "" and not pd.isna(votes):
                        party_records.append(
                            {
                                "party": party,
                                "votes": float(votes),
                            }
                        )

        party_detail = pd.DataFrame(party_records)

        if party_detail.empty:
            st.info("ไม่มี results สำหรับรวมคะแนนรายพรรค")
        else:
            party_detail = (
                party_detail.groupby("party", as_index=False)
                .agg(votes=("votes", "sum"))
                .sort_values("votes", ascending=False)
            )

            party_detail["votes"] = party_detail["votes"].astype(int)

            st.dataframe(
                party_detail,
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("รายการหน่วยในตำบลนี้")

        unit_columns = [
            "unit_type",
            "district",
            "subdistrict",
            "village_no",
            "precinct_no",
            "set_no",
            "winner_party",
            "winner_candidate",
            "winner_votes",
            "runner_up_party",
            "runner_up_votes",
            "margin",
            "total_votes_in_file",
        ]

        available_unit_columns = [
            col
            for col in unit_columns
            if col in selected_rows.columns
        ]

        st.dataframe(
            selected_rows[available_unit_columns],
            use_container_width=True,
            hide_index=True,
        )



# =========================================================
# EDUCATION LEVEL TAB
# =========================================================
with education_tab:
    st.subheader("Education Level Analysis")

    if edu_long.empty:
        st.warning(
            "ไม่พบไฟล์ education_by_agency_district_year.csv "
            "กรุณาวางไฟล์ไว้ในโฟลเดอร์ raw/"
        )
    else:
        st.markdown(
            """
            **สูตรที่ใช้คำนวณระดับการศึกษาเฉลี่ย**

            `ระดับการศึกษาเฉลี่ย = sum(จำนวนคนในแต่ละระดับ × คะแนนระดับการศึกษา) / sum(จำนวนคนทั้งหมด)`

            โดย fix score เป็น:

            | ระดับการศึกษา | คะแนน |
            |---|---:|
            | ก่อนประถมศึกษา | 1 |
            | ประถมศึกษา | 2 |
            | มัธยมศึกษาตอนต้น | 3 |
            | มัธยมศึกษาตอนปลาย / ปวช. | 4 |
            | ปวส. / สูงกว่า | 5 |
            """
        )

        edu_col1, edu_col2, edu_col3 = st.columns([1.2, 1.2, 1.6])

        with edu_col1:
            edu_selected_districts = st.multiselect(
                "เลือกอำเภอสำหรับ Education Level",
                options=DISTRICT_ORDER,
                default=DISTRICT_ORDER,
                key="edu_selected_districts",
            )

        with edu_col2:
            edu_selected_years = st.multiselect(
                "เลือกปีการศึกษา",
                options=[2564, 2565, 2566, 2567, 2568],
                default=[2564, 2565, 2566, 2567, 2568],
                key="edu_selected_years",
            )

        with edu_col3:
            edu_include_advance = st.checkbox(
                "รวมล่วงหน้านอกเขต / นอกราชอาณาจักร ในความสัมพันธ์กับพรรค",
                value=False,
                key="edu_include_advance",
            )

        if not edu_selected_districts:
            st.warning("กรุณาเลือกอย่างน้อย 1 อำเภอ")
            st.stop()

        if not edu_selected_years:
            st.warning("กรุณาเลือกอย่างน้อย 1 ปีการศึกษา")
            st.stop()

        edu_filtered = edu_long[
            edu_long["district"].isin(edu_selected_districts)
            & edu_long["year"].isin(edu_selected_years)
        ].copy()

        edu_avg = build_education_average(
            edu_filtered,
            EDUCATION_SCORE_MAP,
        )

        province_avg = build_province_average(edu_avg)
        period_avg = build_period_average(edu_avg)
        level_dist = build_level_distribution(edu_filtered)

        latest_edu_year = max(edu_selected_years)

        province_latest = province_avg[
            province_avg["year"] == latest_edu_year
        ].copy()

        province_score_latest = (
            province_latest["avg_education_score"].iloc[0]
            if not province_latest.empty
            else np.nan
        )

        period_province = period_avg[
            period_avg["district"] == "ทั้งจังหวัด"
        ].copy()

        score_6466_series = period_province.loc[
            period_province["period"] == "ปี 64-66",
            "avg_education_score",
        ]

        score_6768_series = period_province.loc[
            period_province["period"] == "ปี 67-68",
            "avg_education_score",
        ]

        score_6466 = (
            score_6466_series.iloc[0]
            if len(score_6466_series)
            else np.nan
        )

        score_6768 = (
            score_6768_series.iloc[0]
            if len(score_6768_series)
            else np.nan
        )

        delta_period = (
            score_6768 - score_6466
            if pd.notna(score_6466) and pd.notna(score_6768)
            else np.nan
        )

        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.metric(
                f"ระดับเฉลี่ยทั้งจังหวัด ปี {latest_edu_year}",
                f"{province_score_latest:.2f}" if pd.notna(province_score_latest) else "-",
            )

        with k2:
            st.metric(
                "เฉลี่ยปี 64-66",
                f"{score_6466:.2f}" if pd.notna(score_6466) else "-",
            )

        with k3:
            st.metric(
                "เฉลี่ยปี 67-68",
                f"{score_6768:.2f}" if pd.notna(score_6768) else "-",
                delta=f"{delta_period:.3f}" if pd.notna(delta_period) else None,
            )

        with k4:
            st.metric(
                "จำนวน record การศึกษา",
                f"{len(edu_filtered):,}",
            )

        st.divider()

        edu_overview_tab, edu_district_tab, edu_period_tab, edu_party_tab, edu_raw_tab = st.tabs(
            [
                "Province Overview",
                "District Comparison",
                "64-66 vs 67-68",
                "Party Relationship",
                "Education Raw",
            ]
        )

        # -------------------------
        # Province Overview
        # -------------------------
        with edu_overview_tab:
            st.subheader("ระดับการศึกษาเฉลี่ยของทั้งจังหวัด")

            province_plot = province_avg[
                province_avg["year"].isin(edu_selected_years)
            ].copy()

            fig_province_line = px.line(
                province_plot,
                x="year",
                y="avg_education_score",
                markers=True,
                text="avg_education_score",
                title="ระดับการศึกษาเฉลี่ยของทั้งจังหวัดตามปีการศึกษา",
                labels={
                    "year": "ปีการศึกษา",
                    "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                },
            )

            fig_province_line.update_traces(textposition="top center")
            fig_province_line.update_layout(height=450)

            st.plotly_chart(fig_province_line, use_container_width=True)

            st.dataframe(
                province_plot[
                    [
                        "year",
                        "total_people",
                        "avg_education_score",
                    ]
                ].rename(
                    columns={
                        "year": "ปีการศึกษา",
                        "total_people": "จำนวนรวม",
                        "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("สัดส่วนระดับการศึกษาทั้งจังหวัด")

            province_level = (
                edu_filtered.groupby(["year", "ระดับ"], as_index=False)
                .agg(count=("count", "sum"))
            )

            province_level_total = (
                province_level.groupby("year", as_index=False)
                .agg(total_people=("count", "sum"))
            )

            province_level = province_level.merge(
                province_level_total,
                on="year",
                how="left",
            )

            province_level["share_pct"] = np.where(
                province_level["total_people"] > 0,
                province_level["count"] / province_level["total_people"] * 100,
                0,
            )

            province_level["share_pct"] = province_level["share_pct"].round(2)

            fig_level_stack = px.bar(
                province_level,
                x="year",
                y="share_pct",
                color="ระดับ",
                title="สัดส่วนระดับการศึกษาของทั้งจังหวัดตามปี",
                labels={
                    "year": "ปีการศึกษา",
                    "share_pct": "สัดส่วน (%)",
                    "ระดับ": "ระดับการศึกษา",
                },
                barmode="stack",
            )

            fig_level_stack.update_layout(height=500)

            st.plotly_chart(fig_level_stack, use_container_width=True)

        # -------------------------
        # District Comparison
        # -------------------------
        with edu_district_tab:
            st.subheader("เปรียบเทียบระดับการศึกษาเฉลี่ยรายอำเภอ")

            district_plot = edu_avg[
                edu_avg["district"].isin(edu_selected_districts)
                & edu_avg["year"].isin(edu_selected_years)
            ].copy()

            fig_district_line = px.line(
                district_plot,
                x="year",
                y="avg_education_score",
                color="district",
                markers=True,
                title="ระดับการศึกษาเฉลี่ยรายอำเภอตามปี",
                labels={
                    "year": "ปีการศึกษา",
                    "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                    "district": "อำเภอ",
                },
                category_orders={
                    "district": DISTRICT_ORDER,
                },
            )

            fig_district_line.update_layout(height=500)

            st.plotly_chart(fig_district_line, use_container_width=True)

            fig_district_bar = px.bar(
                district_plot,
                x="district",
                y="avg_education_score",
                color="district",
                facet_col="year",
                title="เปรียบเทียบระดับการศึกษาเฉลี่ยรายอำเภอ แยกตามปี",
                labels={
                    "district": "อำเภอ",
                    "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                    "year": "ปีการศึกษา",
                },
                category_orders={
                    "district": DISTRICT_ORDER,
                },
            )

            fig_district_bar.update_layout(height=500, showlegend=False)

            st.plotly_chart(fig_district_bar, use_container_width=True)

            st.dataframe(
                district_plot.sort_values(["year", "district"]).rename(
                    columns={
                        "district": "อำเภอ",
                        "year": "ปีการศึกษา",
                        "total_people": "จำนวนรวม",
                        "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                    }
                )[
                    [
                        "อำเภอ",
                        "ปีการศึกษา",
                        "จำนวนรวม",
                        "ระดับการศึกษาเฉลี่ย",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
            )

        # -------------------------
        # Period Comparison
        # -------------------------
        with edu_period_tab:
            st.subheader("เปรียบเทียบ ปี 64-66 กับ ปี 67-68")

            period_plot = period_avg[
                period_avg["district"].isin(["ทั้งจังหวัด"] + edu_selected_districts)
            ].copy()

            fig_period = px.bar(
                period_plot,
                x="district",
                y="avg_education_score",
                color="period",
                barmode="group",
                text="avg_education_score",
                title="ระดับการศึกษาเฉลี่ย: ปี 64-66 เทียบกับ ปี 67-68",
                labels={
                    "district": "พื้นที่",
                    "avg_education_score": "ระดับการศึกษาเฉลี่ย",
                    "period": "ช่วงปี",
                },
                category_orders={
                    "district": ["ทั้งจังหวัด"] + DISTRICT_ORDER,
                    "period": ["ปี 64-66", "ปี 67-68"],
                },
            )

            fig_period.update_traces(
                texttemplate="%{text:.2f}",
                textposition="outside",
            )
            fig_period.update_layout(height=500)

            st.plotly_chart(fig_period, use_container_width=True)

            period_wide = period_plot.pivot_table(
                index="district",
                columns="period",
                values="avg_education_score",
                aggfunc="first",
            ).reset_index()

            for col in ["ปี 64-66", "ปี 67-68"]:
                if col not in period_wide.columns:
                    period_wide[col] = np.nan

            period_wide["delta_67_68_minus_64_66"] = (
                period_wide["ปี 67-68"] - period_wide["ปี 64-66"]
            ).round(3)

            fig_delta = px.bar(
                period_wide,
                x="district",
                y="delta_67_68_minus_64_66",
                text="delta_67_68_minus_64_66",
                title="การเปลี่ยนแปลงของระดับการศึกษาเฉลี่ย: ปี 67-68 ลบ ปี 64-66",
                labels={
                    "district": "พื้นที่",
                    "delta_67_68_minus_64_66": "การเปลี่ยนแปลง",
                },
                category_orders={
                    "district": ["ทั้งจังหวัด"] + DISTRICT_ORDER,
                },
            )

            fig_delta.update_traces(
                texttemplate="%{text:.3f}",
                textposition="outside",
            )
            fig_delta.update_layout(height=450)

            st.plotly_chart(fig_delta, use_container_width=True)

            st.dataframe(
                period_wide.rename(
                    columns={
                        "district": "พื้นที่",
                        "ปี 64-66": "ระดับเฉลี่ยปี 64-66",
                        "ปี 67-68": "ระดับเฉลี่ยปี 67-68",
                        "delta_67_68_minus_64_66": "ส่วนต่าง 67-68 ลบ 64-66",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        # -------------------------
        # Party Relationship
        # -------------------------
        with edu_party_tab:
            st.subheader("ความสัมพันธ์ระหว่างพรรคที่ชนะกับระดับการศึกษาเฉลี่ย")

            st.info(
                "พรรคเป็นข้อมูลเชิงกลุ่ม จึงไม่ได้ตีความเป็น correlation ตรง ๆ แบบตัวเลข "
                "หน้านี้ใช้การเปรียบเทียบระดับการศึกษาเฉลี่ยของอำเภอ/ช่วงปี "
                "กับพรรคที่ชนะ และ scatter ระหว่างระดับการศึกษาเฉลี่ยกับ winner share"
            )

            election_for_edu = data[
                (data["election_type"] == selected_type)
                & (data["district"].apply(normalize_district).isin(edu_selected_districts))
            ].copy()

            election_for_edu["district"] = election_for_edu["district"].apply(
                normalize_district
            )

            if not edu_include_advance:
                election_for_edu = election_for_edu[
                    ~is_advance_unit_series(election_for_edu["unit_type"])
                ].copy()

            party_votes_district = build_party_votes_by_district_for_education(
                election_for_edu
            )

            district_winner_edu = build_district_winner_for_education(
                party_votes_district
            )

            if district_winner_edu.empty:
                st.warning("ไม่มีข้อมูลพรรคที่ชนะสำหรับ join กับ education")
            else:
                education_election = district_winner_edu.merge(
                    period_avg[period_avg["district"] != "ทั้งจังหวัด"][
                        [
                            "district",
                            "period",
                            "avg_education_score",
                            "total_people",
                        ]
                    ].rename(
                        columns={
                            "period": "edu_period",
                            "avg_education_score": "avg_education_period",
                            "total_people": "edu_total_people_period",
                        }
                    ),
                    on=["district", "edu_period"],
                    how="left",
                )

                education_election = education_election.sort_values(
                    ["election_year", "district"]
                ).reset_index(drop=True)

                fig_party_bar = px.bar(
                    education_election,
                    x="winner_party",
                    y="avg_education_period",
                    color="winner_party",
                    facet_col="election_year",
                    text="avg_education_period",
                    title="ระดับการศึกษาเฉลี่ยของพื้นที่ แยกตามพรรคที่ชนะ",
                    labels={
                        "winner_party": "พรรคที่ชนะ",
                        "avg_education_period": "ระดับการศึกษาเฉลี่ยของช่วงปี",
                        "election_year": "ปีเลือกตั้ง",
                    },
                    color_discrete_map=PARTY_COLOR_HEX_MAP,
                )

                fig_party_bar.update_traces(
                    texttemplate="%{text:.2f}",
                    textposition="outside",
                )
                fig_party_bar.update_layout(height=500, showlegend=False)

                st.plotly_chart(fig_party_bar, use_container_width=True)

                fig_scatter = px.scatter(
                    education_election,
                    x="avg_education_period",
                    y="winner_share_pct",
                    color="winner_party",
                    size="total_votes",
                    hover_data=[
                        "district",
                        "election_year",
                        "edu_period",
                        "winner_party",
                        "runner_up_party",
                        "margin_pct",
                        "total_votes",
                    ],
                    title="ระดับการศึกษาเฉลี่ย vs คะแนนสัดส่วนของพรรคที่ชนะ",
                    labels={
                        "avg_education_period": "ระดับการศึกษาเฉลี่ยของช่วงปี",
                        "winner_share_pct": "Winner share (%)",
                        "winner_party": "พรรคที่ชนะ",
                        "total_votes": "คะแนนรวม",
                    },
                    color_discrete_map=PARTY_COLOR_HEX_MAP,
                )

                fig_scatter.update_layout(height=550)

                st.plotly_chart(fig_scatter, use_container_width=True)

                if len(education_election) >= 2:
                    corr = education_election[
                        [
                            "avg_education_period",
                            "winner_share_pct",
                            "margin_pct",
                            "total_votes",
                        ]
                    ].corr(numeric_only=True)

                    st.subheader("Numeric Correlation")
                    st.caption(
                        "ตารางนี้ดูเฉพาะตัวแปรตัวเลข เช่น ระดับการศึกษาเฉลี่ย, winner share, margin "
                        "ไม่ใช่ correlation โดยตรงกับชื่อพรรค"
                    )

                    st.dataframe(
                        corr.round(3),
                        use_container_width=True,
                    )

                party_summary = (
                    education_election.groupby("winner_party", as_index=False)
                    .agg(
                        won_district_periods=("district", "count"),
                        avg_education=("avg_education_period", "mean"),
                        min_education=("avg_education_period", "min"),
                        max_education=("avg_education_period", "max"),
                        avg_winner_share=("winner_share_pct", "mean"),
                        avg_margin_pct=("margin_pct", "mean"),
                        total_votes=("total_votes", "sum"),
                    )
                    .sort_values(
                        ["won_district_periods", "avg_education"],
                        ascending=[False, False],
                    )
                )

                party_summary[
                    [
                        "avg_education",
                        "min_education",
                        "max_education",
                        "avg_winner_share",
                        "avg_margin_pct",
                    ]
                ] = party_summary[
                    [
                        "avg_education",
                        "min_education",
                        "max_education",
                        "avg_winner_share",
                        "avg_margin_pct",
                    ]
                ].round(3)

                st.subheader("สรุปรายพรรค")
                st.dataframe(
                    party_summary.rename(
                        columns={
                            "winner_party": "พรรคที่ชนะ",
                            "won_district_periods": "จำนวนอำเภอ/ช่วงที่ชนะ",
                            "avg_education": "ระดับการศึกษาเฉลี่ย",
                            "min_education": "ต่ำสุด",
                            "max_education": "สูงสุด",
                            "avg_winner_share": "Winner share เฉลี่ย",
                            "avg_margin_pct": "Margin เฉลี่ย",
                            "total_votes": "คะแนนรวม",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader("ข้อมูลที่ใช้ join ระหว่าง education กับ election")
                st.dataframe(
                    education_election.rename(
                        columns={
                            "election_year": "ปีเลือกตั้ง",
                            "election_type": "ประเภทบัตร",
                            "district": "อำเภอ",
                            "winner_party": "พรรคที่ชนะ",
                            "winner_votes": "คะแนนพรรคที่ชนะ",
                            "runner_up_party": "พรรคอันดับ 2",
                            "runner_up_votes": "คะแนนอันดับ 2",
                            "total_votes": "คะแนนรวม",
                            "winner_share_pct": "Winner share (%)",
                            "margin_pct": "Margin (%)",
                            "edu_period": "ช่วงปีการศึกษา",
                            "avg_education_period": "ระดับการศึกษาเฉลี่ย",
                            "edu_total_people_period": "จำนวนรวมในข้อมูลการศึกษา",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        # -------------------------
        # Raw Education
        # -------------------------
        with edu_raw_tab:
            st.subheader("Education Long Data")
            st.dataframe(
                edu_filtered,
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Education Average by District-Year")
            st.dataframe(
                edu_avg,
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Province Average")
            st.dataframe(
                province_avg,
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Period Average")
            st.dataframe(
                period_avg,
                use_container_width=True,
                hide_index=True,
            )

            st.subheader("Level Distribution")
            st.dataframe(
                level_dist,
                use_container_width=True,
                hide_index=True,
            )

            with st.expander("Education Debug Info"):
                st.write("Education path:", str(EDU_PATH))
                st.write("Education rows:", len(edu_long))
                st.write("Filtered education rows:", len(edu_filtered))
                st.write("Selected education districts:", edu_selected_districts)
                st.write("Selected education years:", edu_selected_years)
                st.write("Education score map:", EDUCATION_SCORE_MAP)


# =========================================================
# CONSTITUENCY VS PARTY LIST TAB
# =========================================================
with vote_split_tab:
    st.subheader("เปรียบเทียบ สส เขต vs บชรายชื่อ")
    st.caption(
        "ปี 2566 แสดงชื่อพรรคเป็น ‘ก้าวไกล’ และปี 2569 แสดงเป็น ‘ประชาชน’; เฉพาะการสรุปเปรียบเทียบข้ามปีจะนับสองชื่อนี้เป็นกลุ่มเดียวกัน"
    )

    vote_col1, vote_col2, vote_col3, vote_col4 = st.columns([1.1, 1.3, 1.3, 1.1])

    with vote_col1:
        vote_years = st.multiselect(
            "เลือกปีเลือกตั้ง",
            options=[2566, 2569],
            default=[2566, 2569],
            key="vote_split_years",
        )

    available_vote_districts = [
        d for d in DISTRICT_ORDER
        if d in set(data["district"].dropna().astype(str).apply(normalize_district).tolist())
    ]

    with vote_col2:
        vote_districts = st.multiselect(
            "เลือกอำเภอ",
            options=available_vote_districts,
            default=available_vote_districts,
            key="vote_split_districts",
        )

    subdistrict_source_for_vote = data.copy()
    subdistrict_source_for_vote["district_norm"] = subdistrict_source_for_vote["district"].apply(normalize_district)
    subdistrict_source_for_vote["subdistrict_norm"] = subdistrict_source_for_vote["subdistrict"].apply(clean_subdistrict_for_vote)

    if vote_districts:
        subdistrict_source_for_vote = subdistrict_source_for_vote[
            subdistrict_source_for_vote["district_norm"].isin(vote_districts)
        ].copy()

    available_vote_subdistricts = sorted(
        subdistrict_source_for_vote["subdistrict_norm"]
        .dropna()
        .astype(str)
        .str.strip()
        .replace("", np.nan)
        .dropna()
        .unique()
        .tolist()
    )

    with vote_col3:
        vote_subdistricts = st.multiselect(
            "เลือกตำบล (ปล่อยว่าง = ทั้งหมด)",
            options=available_vote_subdistricts,
            default=[],
            key="vote_split_subdistricts",
        )

    with vote_col4:
        vote_scope = st.selectbox(
            "ระดับการรวมข้อมูล",
            options=["รายหน่วย", "รายตำบล", "รายอำเภอ", "รวมทุกพื้นที่"],
            index=0,
            key="vote_split_scope",
        )

    opt_col1, opt_col2, opt_col3 = st.columns([1.1, 1.1, 1.2])

    with opt_col1:
        vote_include_advance = st.checkbox(
            "รวมล่วงหน้านอกเขต / นอกราชอาณาจักร",
            value=False,
            key="vote_split_include_advance",
        )

    with opt_col2:
        top_n_parties = st.slider(
            "จำนวนพรรคที่แสดงในกราฟ",
            min_value=5,
            max_value=30,
            value=15,
            step=1,
            key="vote_split_top_n",
        )

    with opt_col3:
        selected_direction_filter = st.selectbox(
            "กรองประเภทความต่าง",
            options=[
                "ทั้งหมด",
                "เลือกคนมากกว่าพรรค",
                "เลือกพรรคมากกว่าคน",
                "เท่ากัน",
            ],
            index=0,
            key="vote_split_direction_filter",
        )

    if not vote_years:
        st.warning("กรุณาเลือกอย่างน้อย 1 ปีเลือกตั้ง")
    elif not vote_districts:
        st.warning("กรุณาเลือกอย่างน้อย 1 อำเภอ")
    else:
        vote_split_raw = build_party_votes_by_ballot_type(
            source_df=data,
            selected_years=vote_years,
            selected_districts=vote_districts,
            selected_subdistricts=vote_subdistricts,
            include_advance=vote_include_advance,
        )

        if vote_split_raw.empty:
            st.warning("ไม่พบข้อมูลสำหรับเปรียบเทียบ สส เขต กับ บชรายชื่อ ตาม filter ที่เลือก")
        else:
            vote_split_agg = aggregate_vote_split_by_scope(vote_split_raw, vote_scope)
            vote_split_compare = build_constituency_partylist_comparison(vote_split_agg, vote_scope)

            # ใช้รายหน่วยเสมอสำหรับ scatter / T-test แนวโน้ม: 1 จุด = 1 หน่วยในแต่ละตำบล
            vote_split_agg_unit = aggregate_vote_split_by_scope(vote_split_raw, "รายหน่วย")
            vote_split_compare_unit = build_constituency_partylist_comparison(
                vote_split_agg_unit,
                "รายหน่วย",
            )
            vote_split_trend = build_vote_trend_summary(vote_split_compare_unit, "รายหน่วย")

            if selected_direction_filter != "ทั้งหมด" and not vote_split_compare.empty:
                vote_split_compare_filtered = vote_split_compare[
                    vote_split_compare["vote_direction"] == selected_direction_filter
                ].copy()
            else:
                vote_split_compare_filtered = vote_split_compare.copy()

            top_parties_for_chart = (
                vote_split_compare_filtered.groupby("party", as_index=False)
                .agg(total_votes=("total_two_ballots", "sum"))
                .sort_values("total_votes", ascending=False)
                .head(top_n_parties)["party"]
                .tolist()
            )

            top_compare_parties_for_trend = (
                vote_split_compare_filtered.groupby("party_compare_label", as_index=False)
                .agg(total_votes=("total_two_ballots", "sum"))
                .sort_values("total_votes", ascending=False)
                .head(top_n_parties)["party_compare_label"]
                .tolist()
            )

            vote_split_agg_chart = vote_split_agg[
                vote_split_agg["party"].isin(top_parties_for_chart)
            ].copy()

            vote_split_compare_chart = vote_split_compare_filtered[
                vote_split_compare_filtered["party"].isin(top_parties_for_chart)
            ].copy()

            vote_split_unit_chart = vote_split_compare_unit[
                vote_split_compare_unit["party"].isin(top_parties_for_chart)
            ].copy()

            vote_split_trend_chart = vote_split_trend[
                vote_split_trend["party"].isin(top_compare_parties_for_trend)
            ].copy()

            total_constituency = vote_split_compare["constituency_votes"].sum()
            total_partylist = vote_split_compare["partylist_votes"].sum()
            total_gap = total_constituency - total_partylist

            same_direction_count = (
                int((vote_split_trend["trend_alignment"] == "ไปทิศทางเดียวกัน").sum())
                if not vote_split_trend.empty and "trend_alignment" in vote_split_trend.columns
                else 0
            )

            opposite_direction_count = (
                int((vote_split_trend["trend_alignment"] == "ไปคนละทาง").sum())
                if not vote_split_trend.empty and "trend_alignment" in vote_split_trend.columns
                else 0
            )

            m1, m2, m3, m4 = st.columns(4)

            with m1:
                st.metric("คะแนน สส เขต รวม", format_int(total_constituency))

            with m2:
                st.metric("คะแนน บชรายชื่อ รวม", format_int(total_partylist))

            with m3:
                st.metric(
                    "เขต - บชรายชื่อ",
                    format_int(total_gap),
                    help="ค่าบวก = คะแนน สส เขต มากกว่า บชรายชื่อ / ค่าลบ = บชรายชื่อมากกว่า สส เขต",
                )

            with m4:
                st.metric(
                    "รายหน่วยที่ไปคนละทาง",
                    f"{opposite_direction_count:,}",
                    help=f"รายหน่วยที่ไปทิศทางเดียวกัน {same_direction_count:,} รายการ",
                )

            split_tab1, split_tab2, split_tab3, split_tab4 = st.tabs(
                [
                    "กราฟแท่ง เขต vs บช",
                    "เลือกคนหรือเลือกพรรค",
                    "แนวโน้มรายหน่วย",
                    "Raw / Export",
                ]
            )

            # -------------------------
            # 1. Bar compare constituency vs partylist
            # -------------------------
            with split_tab1:
                st.subheader("1) กราฟแท่งเปรียบเทียบ แบ่งเขต vs บชรายชื่อ แต่ละพรรค")

                if vote_split_agg_chart.empty:
                    st.info("ไม่มีข้อมูลสำหรับแสดงกราฟ")
                else:
                    fig_bar = px.bar(
                        vote_split_agg_chart,
                        x="party",
                        y="votes",
                        color="ballot_type",
                        facet_col="year" if len(vote_years) > 1 else None,
                        barmode="group",
                        title="คะแนนเปรียบเทียบ สส เขต vs บชรายชื่อ แยกตามพรรค",
                        labels={
                            "party": "พรรค",
                            "votes": "คะแนน",
                            "ballot_type": "ประเภทบัตร",
                            "year": "ปีเลือกตั้ง",
                        },
                        color_discrete_map={
                            "สส เขต": "#4C78A8",
                            "บชรายชื่อ": "#F58518",
                        },
                    )

                    fig_bar.update_layout(
                        height=560,
                        xaxis_tickangle=-45,
                        legend_title_text="ประเภทบัตร",
                    )

                    st.plotly_chart(fig_bar, use_container_width=True)

                    st.caption(
                        "อ่านค่า: ถ้าแท่ง สส เขต สูงกว่า บชรายชื่อ หมายถึงพรรค/ผู้สมัครในพื้นที่ได้คะแนนจากตัวบุคคลมากกว่าคะแนนพรรคในบัตรบัญชีรายชื่อ"
                    )

                st.subheader("ตารางเปรียบเทียบคะแนนรายพรรค")
                display_cols = [
                    c
                    for c in [
                        "year",
                        "district",
                        "subdistrict",
                        "party",
                        "constituency_votes",
                        "partylist_votes",
                        "person_minus_party_votes",
                        "person_minus_party_pct_of_partylist",
                        "person_minus_party_pct_of_total",
                        "vote_direction",
                    ]
                    if c in vote_split_compare_filtered.columns
                ]

                st.dataframe(
                    vote_split_compare_filtered[display_cols].rename(
                        columns={
                            "year": "ปี",
                            "district": "อำเภอ",
                            "subdistrict": "ตำบล",
                            "party": "พรรค",
                            "constituency_votes": "คะแนน สส เขต",
                            "partylist_votes": "คะแนน บชรายชื่อ",
                            "person_minus_party_votes": "สส เขต - บชรายชื่อ",
                            "person_minus_party_pct_of_partylist": "% ต่างเทียบ บชรายชื่อ",
                            "person_minus_party_pct_of_total": "% ต่างเทียบคะแนนรวมสองบัตร",
                            "vote_direction": "ตีความ",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

            # -------------------------
            # 2. Person vs party gap
            # -------------------------
            with split_tab2:
                st.subheader("2) ดูว่าเลือกคนหรือเลือกพรรค")

                if vote_split_compare_chart.empty:
                    st.info("ไม่มีข้อมูลสำหรับแสดงกราฟ")
                else:
                    fig_gap = px.bar(
                        vote_split_compare_chart.sort_values(
                            ["year", "person_minus_party_votes"],
                            ascending=[True, False],
                        ),
                        x="party",
                        y="person_minus_party_votes",
                        color="vote_direction",
                        facet_col="year" if len(vote_years) > 1 else None,
                        title="ส่วนต่างคะแนน: สส เขต - บชรายชื่อ",
                        labels={
                            "party": "พรรค",
                            "person_minus_party_votes": "ส่วนต่างคะแนน",
                            "vote_direction": "ตีความ",
                            "year": "ปีเลือกตั้ง",
                        },
                        color_discrete_map={
                            "เลือกคนมากกว่าพรรค": "#2ca02c",
                            "เลือกพรรคมากกว่าคน": "#d62728",
                            "เท่ากัน": "#7f7f7f",
                        },
                    )

                    fig_gap.add_hline(y=0, line_dash="dash", line_color="gray")
                    fig_gap.update_layout(height=560, xaxis_tickangle=-45)

                    st.plotly_chart(fig_gap, use_container_width=True)

                    st.markdown(
                        """
                        **วิธีอ่านกราฟ**
                        - ค่าเป็นบวก = คะแนน **สส เขต** มากกว่า **บชรายชื่อ** → มีสัญญาณว่าเลือกคน/ผู้สมัครมากกว่าพรรค
                        - ค่าเป็นลบ = คะแนน **บชรายชื่อ** มากกว่า **สส เขต** → มีสัญญาณว่าเลือกพรรคมากกว่าคน
                        """
                    )

            # -------------------------
            # 3. Subdistrict trend by year
            # -------------------------
            with split_tab3:
                st.subheader("3) แนวโน้มรายหน่วยของแต่ละปี: สส เขต เทียบ บชรายชื่อ")

                st.markdown(
                    """
                    กราฟนี้ใช้ **1 จุด = 1 หน่วยในแต่ละตำบล** โดยแกน X คือคะแนน **บชรายชื่อรายหน่วย** และแกน Y คือคะแนน **สส เขตรายหน่วย**  
                    ถ้าจุดอยู่เหนือเส้นเท่ากัน แปลว่า สส เขต มากกว่า บชรายชื่อ; ถ้าอยู่ใต้เส้น แปลว่า บชรายชื่อมากกว่า สส เขต
                    """
                )

                available_parties_for_scatter = (
                    vote_split_compare_unit.groupby("party_compare_label", as_index=False)
                    .agg(total_votes=("total_two_ballots", "sum"))
                    .sort_values("total_votes", ascending=False)["party_compare_label"]
                    .tolist()
                )

                default_parties = [p for p in ["ก้าวไกล/ประชาชน", "ก้าวไกล", "ประชาชน", "เพื่อไทย", "กล้าธรรม"] if p in available_parties_for_scatter]
                if not default_parties:
                    default_parties = available_parties_for_scatter[:1]

                selected_scatter_parties = st.multiselect(
                    "เลือกพรรคที่ต้องการดูแนวโน้มรายหน่วย",
                    options=available_parties_for_scatter,
                    default=default_parties,
                    key="vote_split_scatter_parties",
                )

                show_district_trend = st.checkbox(
                    "แสดงเส้นแนวโน้มแยกตามอำเภอ",
                    value=True,
                    key="vote_split_show_district_trend",
                )

                if vote_split_compare_unit.empty or not selected_scatter_parties:
                    st.info("ไม่มีข้อมูลสำหรับแสดงแนวโน้มรายหน่วย")
                else:
                    for party_name in selected_scatter_parties:
                        st.markdown(f"### {party_name}")

                        for y in sorted(vote_years):
                            fig_subdistrict_trend = render_subdistrict_trend_scatter(
                                vote_split_compare_unit,
                                party=party_name,
                                year=int(y),
                                show_district_trend=show_district_trend,
                            )
                            st.plotly_chart(fig_subdistrict_trend, use_container_width=True)

                    st.subheader("สรุปแนวโน้มรายหน่วย 66 → 69")

                    trend_cols = [
                        c
                        for c in [
                            "district",
                            "subdistrict",
                            "unit_label",
                            "party",
                            "party_66",
                            "party_69",
                            "direction_66",
                            "direction_69",
                            "gap_change_type",
                            "constituency_trend",
                            "partylist_trend",
                            "trend_alignment",
                            "constituency_delta_69_minus_66",
                            "partylist_delta_69_minus_66",
                            "gap_delta_69_minus_66",
                        ]
                        if c in vote_split_trend_chart.columns
                    ]

                    st.dataframe(
                        vote_split_trend_chart[trend_cols].rename(
                            columns={
                                "district": "อำเภอ",
                                "subdistrict": "ตำบล",
                                "unit_label": "หน่วย",
                                "party": "กลุ่มพรรค",
                                "party_66": "ชื่อพรรคปี 66",
                                "party_69": "ชื่อพรรคปี 69",
                                "direction_66": "ปี 66",
                                "direction_69": "ปี 69",
                                "gap_change_type": "รูปแบบการเปลี่ยน",
                                "constituency_trend": "แนวโน้ม สส เขต",
                                "partylist_trend": "แนวโน้ม บชรายชื่อ",
                                "trend_alignment": "ทิศทางคะแนน 66→69",
                                "constituency_delta_69_minus_66": "Δ สส เขต 69-66",
                                "partylist_delta_69_minus_66": "Δ บช 69-66",
                                "gap_delta_69_minus_66": "Δ ส่วนต่าง 69-66",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.info(
                        "คำว่า 'ไปทิศทางเดียวกัน' หมายถึงคะแนน สส เขต และ บชรายชื่อ ในหน่วยนั้นเพิ่ม/ลดไปทางเดียวกันจากปี 66 ไป 69; "
                        "ส่วน 'ไปคนละทาง' หมายถึงคะแนนประเภทหนึ่งเพิ่ม แต่อีกประเภทลด"
                    )

            # -------------------------
            # 4. Raw / Export
            # -------------------------
            with split_tab4:
                st.subheader("Raw Data สำหรับตรวจสอบ / Export")

                st.write("Raw party votes by ballot type")
                st.dataframe(
                    vote_split_raw,
                    use_container_width=True,
                    hide_index=True,
                )

                st.write("Aggregated votes by selected scope")
                st.dataframe(
                    vote_split_agg,
                    use_container_width=True,
                    hide_index=True,
                )

                st.write("Unit comparison for scatter trend")
                st.dataframe(
                    vote_split_compare_unit,
                    use_container_width=True,
                    hide_index=True,
                )

                st.write("Trend summary 66 → 69 by unit")
                st.dataframe(
                    vote_split_trend,
                    use_container_width=True,
                    hide_index=True,
                )

                csv_compare = vote_split_compare.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "Download selected-scope comparison CSV",
                    data=csv_compare,
                    file_name="constituency_vs_partylist_comparison.csv",
                    mime="text/csv",
                )

                csv_subdistrict = vote_split_compare_unit.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "Download unit comparison CSV",
                    data=csv_subdistrict,
                    file_name="constituency_vs_partylist_unit_comparison.csv",
                    mime="text/csv",
                )

                csv_trend = vote_split_trend.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    "Download unit trend CSV",
                    data=csv_trend,
                    file_name="constituency_vs_partylist_unit_trend_66_69.csv",
                    mime="text/csv",
                )



# =========================================================
# INSIGHT TAB
# =========================================================
def add_ballot_rate_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    numeric_cols = [
        "eligible_voters",
        "appeared_voters",
        "used_ballots",
        "valid_ballots",
        "invalid_ballots",
        "no_vote_ballots",
        "winner_votes",
        "runner_up_votes",
        "margin",
        "total_votes_in_file",
        "winner_share",
        "margin_rate",
    ]

    for col in numeric_cols:
        if col not in out.columns:
            out[col] = 0
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    out["turnout_pct_calc"] = np.where(
        out["eligible_voters"] > 0,
        out["appeared_voters"] / out["eligible_voters"] * 100,
        np.nan,
    )

    out["invalid_pct_calc"] = np.where(
        out["used_ballots"] > 0,
        out["invalid_ballots"] / out["used_ballots"] * 100,
        np.nan,
    )

    out["no_vote_pct_calc"] = np.where(
        out["used_ballots"] > 0,
        out["no_vote_ballots"] / out["used_ballots"] * 100,
        np.nan,
    )

    out["margin_pct_calc"] = np.where(
        out["total_votes_in_file"] > 0,
        out["margin"] / out["total_votes_in_file"] * 100,
        np.nan,
    )

    return out


def summarize_by_subdistrict_for_insight(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    group = (
        df.groupby(["district", "subdistrict"], as_index=False, dropna=False)
        .agg(
            units=("unit_index", "count"),
            eligible_voters=("eligible_voters", "sum"),
            appeared_voters=("appeared_voters", "sum"),
            used_ballots=("used_ballots", "sum"),
            valid_ballots=("valid_ballots", "sum"),
            invalid_ballots=("invalid_ballots", "sum"),
            no_vote_ballots=("no_vote_ballots", "sum"),
            total_votes=("total_votes_in_file", "sum"),
            avg_margin_pct=("margin_pct_calc", "mean"),
            avg_winner_share=("winner_share", "mean"),
        )
    )

    group["turnout_pct"] = np.where(
        group["eligible_voters"] > 0,
        group["appeared_voters"] / group["eligible_voters"] * 100,
        np.nan,
    )

    group["invalid_pct"] = np.where(
        group["used_ballots"] > 0,
        group["invalid_ballots"] / group["used_ballots"] * 100,
        np.nan,
    )

    group["no_vote_pct"] = np.where(
        group["used_ballots"] > 0,
        group["no_vote_ballots"] / group["used_ballots"] * 100,
        np.nan,
    )

    for col in ["turnout_pct", "invalid_pct", "no_vote_pct", "avg_margin_pct", "avg_winner_share"]:
        group[col] = group[col].round(2)

    return group.sort_values(["district", "subdistrict"]).reset_index(drop=True)


def paired_ttest_summary(x: pd.Series, y: pd.Series) -> dict[str, Any]:
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    mask = x.notna() & y.notna()
    x = x[mask].astype(float)
    y = y[mask].astype(float)

    diff = x - y
    n = len(diff)

    base = {
        "n": n,
        "mean_constituency": x.mean() if n else np.nan,
        "mean_partylist": y.mean() if n else np.nan,
        "mean_diff": diff.mean() if n else np.nan,
        "median_diff": diff.median() if n else np.nan,
        "std_diff": diff.std(ddof=1) if n >= 2 else np.nan,
        "se_diff": np.nan,
        "ci95_low": np.nan,
        "ci95_high": np.nan,
        "cohen_dz": np.nan,
        "pct_constituency_gt_partylist": (diff.gt(0).mean() * 100) if n else np.nan,
        "pct_partylist_gt_constituency": (diff.lt(0).mean() * 100) if n else np.nan,
        "t_stat": np.nan,
        "p_value": np.nan,
        "wilcoxon_p_value": np.nan,
        "method": "not enough variance / data",
    }

    if n < 2 or diff.std(ddof=1) == 0:
        return base

    mean_diff = diff.mean()
    std_diff = diff.std(ddof=1)
    se_diff = std_diff / np.sqrt(n)
    t_stat = mean_diff / se_diff
    cohen_dz = mean_diff / std_diff

    p_value = np.nan
    wilcoxon_p_value = np.nan
    ci95_low = np.nan
    ci95_high = np.nan
    method = "manual t-stat only"

    try:
        from scipy import stats

        result = stats.ttest_rel(x, y, nan_policy="omit")
        p_value = float(result.pvalue)

        t_crit = float(stats.t.ppf(0.975, df=n - 1))
        ci95_low = mean_diff - t_crit * se_diff
        ci95_high = mean_diff + t_crit * se_diff

        # Wilcoxon is a non-parametric paired test; useful when vote differences are not normal.
        try:
            w = stats.wilcoxon(x, y, zero_method="wilcox", correction=False, alternative="two-sided")
            wilcoxon_p_value = float(w.pvalue)
        except Exception:
            wilcoxon_p_value = np.nan

        method = "scipy.stats.ttest_rel"
    except Exception:
        p_value = np.nan

    base.update(
        {
            "mean_diff": mean_diff,
            "median_diff": diff.median(),
            "std_diff": std_diff,
            "se_diff": se_diff,
            "ci95_low": ci95_low,
            "ci95_high": ci95_high,
            "cohen_dz": cohen_dz,
            "t_stat": t_stat,
            "p_value": p_value,
            "wilcoxon_p_value": wilcoxon_p_value,
            "method": method,
        }
    )

    return base


def corr_summary(x: pd.Series, y: pd.Series) -> dict[str, Any]:
    x = pd.to_numeric(x, errors="coerce")
    y = pd.to_numeric(y, errors="coerce")
    mask = x.notna() & y.notna()
    x = x[mask].astype(float)
    y = y[mask].astype(float)

    if len(x) < 2 or x.nunique() < 2 or y.nunique() < 2:
        return {"n": len(x), "pearson_r": np.nan, "p_value": np.nan, "method": "not enough variance / data"}

    try:
        from scipy import stats

        r, p = stats.pearsonr(x, y)
        return {"n": len(x), "pearson_r": float(r), "p_value": float(p), "method": "scipy.stats.pearsonr"}
    except Exception:
        return {"n": len(x), "pearson_r": float(np.corrcoef(x, y)[0, 1]), "p_value": np.nan, "method": "numpy corrcoef"}


def format_p_value(p: Any) -> str:
    try:
        if pd.isna(p):
            return "-"
        if p < 0.001:
            return f"{p:.2e}"
        return f"{p:.4f}"
    except Exception:
        return "-"


with insight_tab:
    st.subheader("Insight & Statistical Visualizations")
    st.caption(
        "รวม visualization สำหรับสถิติที่น่าจับตามอง เช่น turnout, บัตรเสีย, no vote, margin, winner share, paired t-test และ ticket splitting correlation"
    )

    insight_control1, insight_control2, insight_control3, insight_control4 = st.columns([1.0, 1.0, 1.4, 1.2])

    with insight_control1:
        insight_year = st.selectbox(
            "ปีสำหรับ Insight",
            options=year_options,
            index=year_options.index(selected_year) if selected_year in year_options else 0,
            format_func=lambda x: f"ปี {x}",
            key="insight_year",
        )

    insight_year_source = data[data["year"] == insight_year].copy()
    insight_type_options = sorted(insight_year_source["election_type"].dropna().astype(str).unique().tolist())

    with insight_control2:
        insight_type = st.selectbox(
            "ประเภทบัตร",
            options=insight_type_options,
            index=insight_type_options.index(selected_type) if selected_type in insight_type_options else 0,
            format_func=lambda x: "บัญชีรายชื่อ" if normalize_election_type_key(x) == "partylist" else "แบ่งเขต",
            key="insight_type",
        )

    insight_districts_all = [
        d for d in DISTRICT_ORDER
        if d in set(insight_year_source["district"].dropna().astype(str).apply(normalize_district).tolist())
    ]

    with insight_control3:
        insight_districts = st.multiselect(
            "เลือกอำเภอ",
            options=insight_districts_all,
            default=insight_districts_all,
            key="insight_districts",
        )

    with insight_control4:
        insight_include_advance = st.checkbox(
            "รวมล่วงหน้านอกเขต / นอกราชอาณาจักร",
            value=False,
            key="insight_include_advance",
        )

    insight_df = data[
        (data["year"] == insight_year)
        & (data["election_type"] == insight_type)
    ].copy()

    insight_df["district"] = insight_df["district"].apply(normalize_district)

    if insight_districts:
        insight_df = insight_df[insight_df["district"].isin(insight_districts)].copy()

    if not insight_include_advance:
        insight_df = insight_df[~is_advance_unit_series(insight_df["unit_type"])].copy()

    insight_df = add_ballot_rate_columns(insight_df)

    if insight_df.empty:
        st.warning("ไม่มีข้อมูลสำหรับ Insight ตาม filter ที่เลือก")
    else:
        total_units = len(insight_df)
        total_eligible = insight_df["eligible_voters"].sum()
        total_appeared = insight_df["appeared_voters"].sum()
        total_used = insight_df["used_ballots"].sum()
        total_invalid = insight_df["invalid_ballots"].sum()
        total_no_vote = insight_df["no_vote_ballots"].sum()
        total_valid = insight_df["valid_ballots"].sum()

        overall_turnout = total_appeared / total_eligible * 100 if total_eligible > 0 else np.nan
        overall_invalid = total_invalid / total_used * 100 if total_used > 0 else np.nan
        overall_no_vote = total_no_vote / total_used * 100 if total_used > 0 else np.nan
        avg_margin = insight_df["margin_pct_calc"].mean()

        close_units = int((insight_df["margin_pct_calc"] <= CLOSE_RACE_THRESHOLD_PCT).sum())
        landslide_units = int((insight_df["margin_pct_calc"] >= LANDSLIDE_THRESHOLD_PCT).sum())

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        with kpi1:
            st.metric("จำนวนหน่วย", f"{total_units:,}")
        with kpi2:
            st.metric("Turnout", f"{overall_turnout:.2f}%" if pd.notna(overall_turnout) else "-")
        with kpi3:
            st.metric("Invalid ballots", f"{overall_invalid:.2f}%" if pd.notna(overall_invalid) else "-")
        with kpi4:
            st.metric("No vote", f"{overall_no_vote:.2f}%" if pd.notna(overall_no_vote) else "-")
        with kpi5:
            st.metric("Avg margin", f"{avg_margin:.2f}%" if pd.notna(avg_margin) else "-")

        st.divider()

        desc_tab, turnout_tab, invalid_tab, winner_tab, margin_tab, split_stats_tab, export_insight_tab = st.tabs(
            [
                "Descriptive",
                "Turnout",
                "Invalid / No vote",
                "Winner",
                "Margin",
                "T-Test & Correlation",
                "Raw / Export",
            ]
        )

        subdistrict_summary = summarize_by_subdistrict_for_insight(
            insight_df[
                insight_df["subdistrict"].fillna("").astype(str).str.strip().ne("")
            ].copy()
        )

        # -------------------------
        # Descriptive Statistics
        # -------------------------
        with desc_tab:
            st.subheader("Descriptive Statistics")

            pie_col, bar_col = st.columns([1.0, 1.4])

            with pie_col:
                audit_counts = (
                    insight_df["audit_level"]
                    .fillna("ไม่ระบุ")
                    .astype(str)
                    .value_counts()
                    .reset_index()
                )
                audit_counts.columns = ["audit_level", "units"]

                fig_audit = px.pie(
                    audit_counts,
                    names="audit_level",
                    values="units",
                    title="สัดส่วนระดับ Audit ของหน่วยเลือกตั้ง",
                    hole=0.35,
                )
                fig_audit.update_layout(height=420)
                st.plotly_chart(fig_audit, use_container_width=True)

            with bar_col:
                winner_counts = (
                    insight_df.groupby("winner_party", as_index=False)
                    .agg(
                        won_units=("unit_index", "count"),
                        total_winner_votes=("winner_votes", "sum"),
                    )
                    .sort_values("won_units", ascending=False)
                    .head(12)
                )

                fig_winner_units = px.bar(
                    winner_counts,
                    x="winner_party",
                    y="won_units",
                    color="winner_party",
                    title="จำนวนหน่วยที่แต่ละพรรคชนะมากที่สุด",
                    labels={
                        "winner_party": "พรรคที่ชนะ",
                        "won_units": "จำนวนหน่วย",
                    },
                    color_discrete_map=PARTY_COLOR_HEX_MAP,
                )
                fig_winner_units.update_layout(height=420, showlegend=False, xaxis_tickangle=-35)
                st.plotly_chart(fig_winner_units, use_container_width=True)

            st.subheader("Summary table")
            summary_table = pd.DataFrame(
                [
                    {"metric": "eligible_voters", "value": total_eligible},
                    {"metric": "appeared_voters", "value": total_appeared},
                    {"metric": "used_ballots", "value": total_used},
                    {"metric": "valid_ballots", "value": total_valid},
                    {"metric": "invalid_ballots", "value": total_invalid},
                    {"metric": "no_vote_ballots", "value": total_no_vote},
                    {"metric": "close_race_units_<=5pct", "value": close_units},
                    {"metric": "landslide_units_>=15pct", "value": landslide_units},
                ]
            )
            st.dataframe(summary_table, use_container_width=True, hide_index=True)

        # -------------------------
        # Voter Turnout Analysis
        # -------------------------
        with turnout_tab:
            st.subheader("Voter Turnout Analysis")

            fig_turnout_scatter = px.scatter(
                insight_df,
                x="eligible_voters",
                y="appeared_voters",
                color="district",
                size="invalid_ballots",
                hover_data=[
                    "subdistrict",
                    "village_no",
                    "precinct_no",
                    "winner_party",
                    "turnout_pct_calc",
                    "invalid_pct_calc",
                    "no_vote_pct_calc",
                ],
                title="Eligible voters vs Appeared voters รายหน่วย",
                labels={
                    "eligible_voters": "ผู้มีสิทธิเลือกตั้ง",
                    "appeared_voters": "ผู้มาใช้สิทธิ",
                    "district": "อำเภอ",
                    "invalid_ballots": "บัตรเสีย",
                },
            )

            max_turnout_axis = max(
                float(insight_df["eligible_voters"].max()),
                float(insight_df["appeared_voters"].max()),
            )
            fig_turnout_scatter.add_trace(
                go.Scatter(
                    x=[0, max_turnout_axis],
                    y=[0, max_turnout_axis],
                    mode="lines",
                    name="เส้น appeared = eligible",
                    line=dict(color="gray", dash="dash"),
                    hoverinfo="skip",
                )
            )
            fig_turnout_scatter.update_layout(height=560)
            st.plotly_chart(fig_turnout_scatter, use_container_width=True)

            if not subdistrict_summary.empty:
                top_turnout = subdistrict_summary.sort_values("turnout_pct", ascending=False).head(10)
                low_turnout = subdistrict_summary.sort_values("turnout_pct", ascending=True).head(10)

                tc1, tc2 = st.columns(2)

                with tc1:
                    fig_top_turnout = px.bar(
                        top_turnout,
                        x="turnout_pct",
                        y="subdistrict",
                        color="district",
                        orientation="h",
                        title="10 ตำบล turnout สูงสุด",
                        labels={"turnout_pct": "Turnout (%)", "subdistrict": "ตำบล"},
                    )
                    fig_top_turnout.update_layout(height=450, yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_top_turnout, use_container_width=True)

                with tc2:
                    fig_low_turnout = px.bar(
                        low_turnout,
                        x="turnout_pct",
                        y="subdistrict",
                        color="district",
                        orientation="h",
                        title="10 ตำบล turnout ต่ำสุด",
                        labels={"turnout_pct": "Turnout (%)", "subdistrict": "ตำบล"},
                    )
                    fig_low_turnout.update_layout(height=450, yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_low_turnout, use_container_width=True)

        # -------------------------
        # Invalid ballot / No vote
        # -------------------------
        with invalid_tab:
            st.subheader("Invalid Ballot & No Vote Analysis")

            if subdistrict_summary.empty:
                st.info("ไม่มีข้อมูลรายตำบลสำหรับวิเคราะห์")
            else:
                invalid_col, novote_col = st.columns(2)

                top_invalid = subdistrict_summary.sort_values("invalid_pct", ascending=False).head(10)
                top_novote = subdistrict_summary.sort_values("no_vote_pct", ascending=False).head(10)

                with invalid_col:
                    fig_invalid = px.bar(
                        top_invalid,
                        x="invalid_pct",
                        y="subdistrict",
                        color="district",
                        orientation="h",
                        title="10 อันดับตำบลที่มีสัดส่วนบัตรเสียสูงสุด",
                        labels={"invalid_pct": "บัตรเสีย (%)", "subdistrict": "ตำบล"},
                    )
                    fig_invalid.update_layout(height=500, yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_invalid, use_container_width=True)

                with novote_col:
                    fig_novote = px.bar(
                        top_novote,
                        x="no_vote_pct",
                        y="subdistrict",
                        color="district",
                        orientation="h",
                        title="10 อันดับตำบลที่ไม่เลือกผู้ใดสูงสุด",
                        labels={"no_vote_pct": "ไม่เลือกผู้ใด (%)", "subdistrict": "ตำบล"},
                    )
                    fig_novote.update_layout(height=500, yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig_novote, use_container_width=True)

                fig_invalid_novote = px.scatter(
                    subdistrict_summary,
                    x="invalid_pct",
                    y="no_vote_pct",
                    size="used_ballots",
                    color="district",
                    hover_data=["subdistrict", "units", "used_ballots", "turnout_pct"],
                    title="ความสัมพันธ์ระหว่างบัตรเสียกับไม่เลือกผู้ใด รายตำบล",
                    labels={
                        "invalid_pct": "บัตรเสีย (%)",
                        "no_vote_pct": "ไม่เลือกผู้ใด (%)",
                        "used_ballots": "จำนวนบัตรใช้แล้ว",
                    },
                )
                fig_invalid_novote.update_layout(height=560)
                st.plotly_chart(fig_invalid_novote, use_container_width=True)

        # -------------------------
        # Winner Analysis
        # -------------------------
        with winner_tab:
            st.subheader("Winner Analysis")

            fig_winner_share = px.histogram(
                insight_df,
                x="winner_share",
                color="winner_party",
                nbins=25,
                title="Distribution ของ winner share รายหน่วย",
                labels={"winner_share": "Winner share (%)", "winner_party": "พรรคที่ชนะ"},
                color_discrete_map=PARTY_COLOR_HEX_MAP,
            )
            fig_winner_share.update_layout(height=520)
            st.plotly_chart(fig_winner_share, use_container_width=True)

            win_by_district = (
                insight_df.groupby(["district", "winner_party"], as_index=False)
                .agg(
                    won_units=("unit_index", "count"),
                    total_winner_votes=("winner_votes", "sum"),
                    avg_winner_share=("winner_share", "mean"),
                )
                .sort_values(["district", "won_units"], ascending=[True, False])
            )
            win_by_district["avg_winner_share"] = win_by_district["avg_winner_share"].round(2)

            fig_win_district = px.bar(
                win_by_district,
                x="district",
                y="won_units",
                color="winner_party",
                title="จำนวนหน่วยที่ชนะ แยกรายอำเภอและพรรค",
                labels={"district": "อำเภอ", "won_units": "จำนวนหน่วย", "winner_party": "พรรคที่ชนะ"},
                color_discrete_map=PARTY_COLOR_HEX_MAP,
            )
            fig_win_district.update_layout(height=520)
            st.plotly_chart(fig_win_district, use_container_width=True)

            st.dataframe(
                win_by_district.rename(
                    columns={
                        "district": "อำเภอ",
                        "winner_party": "พรรคที่ชนะ",
                        "won_units": "จำนวนหน่วยที่ชนะ",
                        "total_winner_votes": "คะแนนผู้ชนะรวม",
                        "avg_winner_share": "Winner share เฉลี่ย (%)",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        # -------------------------
        # Margin Distribution
        # -------------------------
        with margin_tab:
            st.subheader("Margin Distribution Analysis")

            insight_df["margin_category"] = np.select(
                [
                    insight_df["margin_pct_calc"] <= CLOSE_RACE_THRESHOLD_PCT,
                    insight_df["margin_pct_calc"] >= LANDSLIDE_THRESHOLD_PCT,
                ],
                [
                    "สูสี ≤ 5%",
                    "ชนะขาด ≥ 15%",
                ],
                default="ทั่วไป",
            )

            fig_margin_hist = px.histogram(
                insight_df,
                x="margin_pct_calc",
                color="margin_category",
                nbins=30,
                title="การกระจาย margin ระหว่างอันดับ 1 กับอันดับ 2 รายหน่วย",
                labels={"margin_pct_calc": "Margin (%)", "margin_category": "ประเภทการแข่งขัน"},
                color_discrete_map={
                    "สูสี ≤ 5%": "#d62728",
                    "ทั่วไป": "#7f7f7f",
                    "ชนะขาด ≥ 15%": "#2ca02c",
                },
            )
            fig_margin_hist.add_vline(x=CLOSE_RACE_THRESHOLD_PCT, line_dash="dash", line_color="red")
            fig_margin_hist.add_vline(x=LANDSLIDE_THRESHOLD_PCT, line_dash="dash", line_color="green")
            fig_margin_hist.update_layout(height=520)
            st.plotly_chart(fig_margin_hist, use_container_width=True)

            margin_by_party = (
                insight_df.groupby(["winner_party", "margin_category"], as_index=False)
                .agg(units=("unit_index", "count"))
            )

            fig_margin_party = px.bar(
                margin_by_party,
                x="winner_party",
                y="units",
                color="margin_category",
                title="จำนวนหน่วยที่สูสี / ทั่วไป / ชนะขาด แยกตามพรรคที่ชนะ",
                labels={"winner_party": "พรรคที่ชนะ", "units": "จำนวนหน่วย", "margin_category": "ประเภทการแข่งขัน"},
                color_discrete_map={
                    "สูสี ≤ 5%": "#d62728",
                    "ทั่วไป": "#7f7f7f",
                    "ชนะขาด ≥ 15%": "#2ca02c",
                },
            )
            fig_margin_party.update_layout(height=520, xaxis_tickangle=-35)
            st.plotly_chart(fig_margin_party, use_container_width=True)

            st.subheader("หน่วยที่สูสีที่สุด")
            close_table = insight_df.sort_values("margin_pct_calc", ascending=True).head(20)
            st.dataframe(
                close_table[
                    [
                        "district",
                        "subdistrict",
                        "village_no",
                        "precinct_no",
                        "winner_party",
                        "winner_votes",
                        "runner_up_party",
                        "runner_up_votes",
                        "margin",
                        "margin_pct_calc",
                        "total_votes_in_file",
                    ]
                ].rename(
                    columns={
                        "district": "อำเภอ",
                        "subdistrict": "ตำบล",
                        "village_no": "หมู่",
                        "precinct_no": "หน่วย",
                        "winner_party": "อันดับ 1",
                        "winner_votes": "คะแนนอันดับ 1",
                        "runner_up_party": "อันดับ 2",
                        "runner_up_votes": "คะแนนอันดับ 2",
                        "margin": "ส่วนต่างคะแนน",
                        "margin_pct_calc": "ส่วนต่าง (%)",
                        "total_votes_in_file": "คะแนนรวม",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        # -------------------------
        # T-Test & Correlation
        # -------------------------
        with split_stats_tab:
            st.subheader("Paired T-Test & Ticket Splitting Correlation")
            st.caption(
                "ส่วนนี้จับคู่คะแนน สส เขต กับ บชรายชื่อในหน่วยเดียวกัน แล้วทดสอบว่าคะแนนสองบัตรต่างกันอย่างมีนัยสำคัญหรือไม่"
            )

            split_raw_for_stats = build_party_votes_by_ballot_type(
                source_df=data,
                selected_years=[2566, 2569],
                selected_districts=insight_districts,
                selected_subdistricts=None,
                include_advance=insight_include_advance,
            )

            if split_raw_for_stats.empty:
                st.info("ไม่มีข้อมูลสำหรับ ticket splitting")
            else:
                split_unit = aggregate_vote_split_by_scope(split_raw_for_stats, "รายหน่วย")
                split_compare_unit = build_constituency_partylist_comparison(split_unit, "รายหน่วย")

                # พรรคสำหรับ T-Test ใช้ชื่อจริงตามปีที่เลือก: ปี 2566 = ก้าวไกล, ปี 2569 = ประชาชน
                party_options_by_year = {}
                for y in [2566, 2569]:
                    party_options_by_year[y] = (
                        split_compare_unit[split_compare_unit["year"] == y]
                        .groupby("party", as_index=False)
                        .agg(total_votes=("total_two_ballots", "sum"))
                        .sort_values("total_votes", ascending=False)["party"]
                        .tolist()
                    )

                stat_col1, stat_col2 = st.columns([1.0, 1.0])

                with stat_col1:
                    stat_year = st.selectbox(
                        "เลือกปีสำหรับ T-Test / Correlation",
                        options=[2566, 2569],
                        index=0 if insight_year == 2566 else 1,
                        key="insight_stat_year",
                    )

                party_options = party_options_by_year.get(stat_year, [])
                default_party_idx = 0
                preferred = ["ก้าวไกล", "ประชาชน", "เพื่อไทย", "กล้าธรรม"]
                for i, p in enumerate(party_options):
                    if p in preferred:
                        default_party_idx = i
                        break

                with stat_col2:
                    stat_party = st.selectbox(
                        "เลือกพรรค",
                        options=party_options,
                        index=default_party_idx if party_options else 0,
                        key=f"insight_stat_party_{stat_year}",
                    )

                stat_df = split_compare_unit[
                    (split_compare_unit["year"] == stat_year)
                    & (split_compare_unit["party"] == stat_party)
                    & (split_compare_unit["constituency_votes"] > 0)
                    & (split_compare_unit["partylist_votes"] > 0)
                ].copy()

                if stat_df.empty:
                    st.info("ไม่มีข้อมูลสำหรับพรรค/ปีที่เลือก")
                else:
                    ttest = paired_ttest_summary(
                        stat_df["constituency_votes"],
                        stat_df["partylist_votes"],
                    )
                    corr = corr_summary(
                        stat_df["partylist_votes"],
                        stat_df["constituency_votes"],
                    )

                    tt1, tt2, tt3, tt4, tt5 = st.columns(5)
                    with tt1:
                        st.metric("จำนวนคู่ข้อมูล", f"{ttest['n']:,}")
                    with tt2:
                        st.metric("Mean สส เขต", format_number(ttest["mean_constituency"]))
                    with tt3:
                        st.metric("Mean บชรายชื่อ", format_number(ttest["mean_partylist"]))
                    with tt4:
                        st.metric("t-stat", format_number(ttest["t_stat"], 3))
                    with tt5:
                        st.metric("p-value", format_p_value(ttest["p_value"]))

                    if ttest["n"] < 2:
                        st.warning(
                            "มีคู่ข้อมูลน้อยกว่า 2 คู่ จึงคำนวณ t-test และ Pearson correlation ไม่ได้ "
                            "ถ้าเห็นค่านี้ให้ตรวจสอบว่ามีทั้งบัตรแบ่งเขตและบัญชีรายชื่อในระดับหน่วยเดียวกันหรือไม่"
                        )

                    corr1, corr2, corr3 = st.columns(3)
                    with corr1:
                        st.metric("Pearson r", format_number(corr["pearson_r"], 3))
                    with corr2:
                        st.metric("Correlation p-value", format_p_value(corr["p_value"]))
                    with corr3:
                        st.metric("Mean เขต - บช", format_number(ttest["mean_diff"], 2))

                    eff1, eff2, eff3, eff4 = st.columns(4)
                    with eff1:
                        st.metric("Median เขต - บช", format_number(ttest["median_diff"], 2))
                    with eff2:
                        st.metric("Cohen's dz", format_number(ttest["cohen_dz"], 3))
                    with eff3:
                        ci_text = (
                            f"[{format_number(ttest['ci95_low'], 1)}, {format_number(ttest['ci95_high'], 1)}]"
                            if pd.notna(ttest["ci95_low"]) and pd.notna(ttest["ci95_high"])
                            else "-"
                        )
                        st.metric("95% CI ของส่วนต่าง", ci_text)
                    with eff4:
                        st.metric("Wilcoxon p-value", format_p_value(ttest["wilcoxon_p_value"]))

                    direction_diag = pd.DataFrame(
                        [
                            {
                                "รายการตรวจสอบ": "หน่วยที่ สส เขต > บชรายชื่อ",
                                "ค่า": f"{ttest['pct_constituency_gt_partylist']:.1f}%",
                            },
                            {
                                "รายการตรวจสอบ": "หน่วยที่ บชรายชื่อ > สส เขต",
                                "ค่า": f"{ttest['pct_partylist_gt_constituency']:.1f}%",
                            },
                            {
                                "รายการตรวจสอบ": "จำนวนอำเภอที่ใช้คำนวณ",
                                "ค่า": stat_df["district"].nunique() if "district" in stat_df.columns else "-",
                            },
                            {
                                "รายการตรวจสอบ": "จำนวนตำบลที่ใช้คำนวณ",
                                "ค่า": stat_df["subdistrict"].nunique() if "subdistrict" in stat_df.columns else "-",
                            },
                        ]
                    )
                    st.dataframe(direction_diag, use_container_width=True, hide_index=True)

                    if pd.notna(ttest["p_value"]) and ttest["p_value"] < 0.001:
                        st.info(
                            "p-value เล็กมากได้เป็นปกติเมื่อจำนวนหน่วยเยอะและคะแนนสองบัตรต่างกันสม่ำเสมอ "
                            "ให้ดูขนาดผลร่วมด้วย เช่น Mean/Median เขต-บช, 95% CI และ Cohen's dz ไม่ควรดู p-value อย่างเดียว"
                        )

                    hover_cols = [
                        col
                        for col in [
                            "subdistrict",
                            "unit_label",
                            "person_minus_party_votes",
                            "vote_direction",
                        ]
                        if col in stat_df.columns
                    ]

                    fig_ticket_scatter = px.scatter(
                        stat_df,
                        x="partylist_votes",
                        y="constituency_votes",
                        color="district" if "district" in stat_df.columns else None,
                        hover_data=hover_cols,
                        title=f"Ticket splitting correlation: {stat_party} ปี {stat_year}",
                        labels={
                            "partylist_votes": "คะแนน บชรายชื่อ รายหน่วย",
                            "constituency_votes": "คะแนน สส เขต รายหน่วย",
                            "district": "อำเภอ",
                        },
                    )

                    max_axis = max(float(stat_df["partylist_votes"].max()), float(stat_df["constituency_votes"].max()))
                    fig_ticket_scatter.add_trace(
                        go.Scatter(
                            x=[0, max_axis],
                            y=[0, max_axis],
                            mode="lines",
                            name="เส้นเท่ากัน",
                            line=dict(color="gray", dash="dash"),
                            hoverinfo="skip",
                        )
                    )

                    if len(stat_df) >= 2 and stat_df["partylist_votes"].nunique() >= 2:
                        x = stat_df["partylist_votes"].astype(float).to_numpy()
                        y = stat_df["constituency_votes"].astype(float).to_numpy()
                        slope, intercept = np.polyfit(x, y, 1)
                        xs = np.linspace(x.min(), x.max(), 100)
                        fig_ticket_scatter.add_trace(
                            go.Scatter(
                                x=xs,
                                y=slope * xs + intercept,
                                mode="lines",
                                name="Trendline",
                                line=dict(color="black", width=2),
                                hoverinfo="skip",
                            )
                        )

                    fig_ticket_scatter.update_layout(height=580)
                    st.plotly_chart(fig_ticket_scatter, use_container_width=True)

                    st.markdown(
                        """
                        **วิธีอ่านผล**  
                        - `p-value < 0.05` มักตีความได้ว่าคะแนน สส เขต กับ บชรายชื่อแตกต่างกันอย่างมีนัยสำคัญ  
                        - `Pearson r` ใกล้ 1 หมายถึงคะแนนสองบัตรไปในทิศทางเดียวกันสูง  
                        - จุดเหนือเส้นเท่ากัน = คะแนน สส เขต มากกว่า บชรายชื่อ / จุดใต้เส้น = บชรายชื่อมากกว่า สส เขต
                        """
                    )

        # -------------------------
        # Raw / Export
        # -------------------------
        with export_insight_tab:
            st.subheader("Raw / Export")

            st.write("Insight unit data")
            st.dataframe(
                insight_df.drop(columns=["results"], errors="ignore"),
                use_container_width=True,
                hide_index=True,
            )

            st.write("Subdistrict summary")
            st.dataframe(subdistrict_summary, use_container_width=True, hide_index=True)

            st.download_button(
                "Download insight unit data CSV",
                data=insight_df.drop(columns=["results"], errors="ignore").to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"insight_unit_data_{insight_year}_{insight_type}.csv",
                mime="text/csv",
            )

            st.download_button(
                "Download subdistrict summary CSV",
                data=subdistrict_summary.to_csv(index=False, encoding="utf-8-sig"),
                file_name=f"insight_subdistrict_summary_{insight_year}_{insight_type}.csv",
                mime="text/csv",
            )

# =========================================================
# RAW TAB
# =========================================================
with raw_tab:
    st.subheader(f"Filtered Unit Data - ปี {selected_year}")

    st.dataframe(
        filtered_data.drop(columns=["results"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Area Filtered Data Used for Choropleth")

    st.dataframe(
        area_filtered_data.drop(columns=["results"], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Aggregated Subdistrict Winner Data")

    st.dataframe(
        area_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Display Stats Used for Map")

    st.dataframe(
        display_stats.drop(columns=[], errors="ignore"),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Comparison Data 66/69")

    st.dataframe(
        comparison_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Close Race Data")

    st.dataframe(
        close_race_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Landslide Data")

    st.dataframe(
        landslide_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Overall Summary Data Used for KPI")

    st.dataframe(
        overall_summary_stats,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Party Unit Wins by Subdistrict")

    st.dataframe(
        party_unit_wins_by_subdistrict,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Advance Unit Data")

    if advance_stats.empty:
        st.info("ไม่มี advance unit")
    else:
        st.dataframe(
            advance_stats.drop(columns=["results"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Advance Hex Layer Data")

    if advance_hex_data.empty:
        st.info("ไม่มี advance hex layer data")
    else:
        st.dataframe(
            advance_hex_data.drop(columns=["polygon"], errors="ignore"),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("GeoJSON Match Preview")

    preview_rows = []

    for feature in choropleth_geojson.get("features", [])[:50]:
        props = feature.get("properties", {})

        preview_rows.append(
            {
                "adm2 / district": props.get("geo_district"),
                "adm3 / subdistrict": props.get("geo_subdistrict"),
                "area_key": props.get("area_key"),
                "has_data": props.get("has_data"),
                "display_note": props.get("display_note"),
                "winner_party": props.get("winner_party"),
                "winner_votes": props.get("winner_votes"),
                "margin_pct": props.get("margin_pct"),
                "line_color": props.get("line_color"),
                "fill_color": props.get("fill_color"),
            }
        )

    st.dataframe(
        pd.DataFrame(preview_rows),
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Debug Info"):
        geo_features = choropleth_geojson.get("features", [])

        matched_features = sum(
            1
            for f in geo_features
            if f.get("properties", {}).get("has_data") is True
        )

        st.write("Selected year:", selected_year)
        st.write("Election type:", selected_type)
        st.write("Display mode:", display_mode)
        st.write("Close race threshold:", CLOSE_RACE_THRESHOLD_PCT)
        st.write("Landslide threshold:", LANDSLIDE_THRESHOLD_PCT)
        st.write("Filtered unit rows:", len(filtered_data))
        st.write("Area filtered unit rows:", len(area_filtered_data))
        st.write("Advance rows:", len(advance_stats))
        st.write("Advance hex rows:", len(advance_hex_data))
        st.write("Overall summary rows:", len(overall_summary_stats))
        st.write("Party unit wins rows:", len(party_unit_wins_by_subdistrict))
        st.write("Aggregated subdistrict rows:", len(area_stats))
        st.write("Comparison rows:", len(comparison_stats))
        st.write("Close race rows:", len(close_race_stats))
        st.write("Landslide rows:", len(landslide_stats))
        st.write("GeoJSON features:", len(geo_features))
        st.write("Matched GeoJSON features:", matched_features)
        st.write("Unmatched GeoJSON features:", len(geo_features) - matched_features)
        st.write("GeoJSON path:", str(GEOJSON_PATH))
        st.write("CSV path:", str(DATA_PATH))
        st.write("Map center:", map_lat, map_lon)