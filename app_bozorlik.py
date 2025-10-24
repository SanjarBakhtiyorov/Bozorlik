# -*- coding: utf-8 -*-
"""
Bozorlik ilovasi (Streamlit): Reja → Xarid → Tahlil
- 1) Reja: mahsulot, kategoriya, birlik, reja miqdori
- 2) Bozorda: cheklist, real miqdor va narx (QQS bilan), QQS ajratish
- 3) Tahlil: kategoriyalar bo'yicha sarf, QQS, Net/Gross, reja vs fakt
Ishga tushirish:  $ streamlit run app_bozorlik.py
"""

import streamlit as st
# ⚠️ Eng birinchi Streamlit chaqiruvi bo‘lishi shart:
st.set_page_config(page_title="Bozorlik | Reja → Xarid → Tahlil", page_icon="🛒", layout="wide")

import io
import pandas as pd

# Altair optional (charts)
try:
    import altair as alt
    ALTAIR_OK = True
except Exception:
    ALTAIR_OK = False

# --- Constants & helpers ---
DEFAULT_QQS = 12.0  # %
UNITS_FLOAT = {"kg", "litr"}
UNITS_INT = {"dona", "karobka"}
ALL_UNITS = ["kg", "litr", "dona", "karobka"]

DEFAULT_CATEGORIES = [
    "Meva-sabzavot",
    "Quruq oziq-ovqat",
    "Ichimliklar",
    "Sut mahsulotlari",
    "Shirinliklar",
    "Non & bakery",
    "Uy-ro'zg'or",
    "Boshqa",
]

# Tez tanlash uchun (unit + default category)
COMMON_ITEMS = {
    "anor": ("kg", "Meva-sabzavot"),
    "olma": ("kg", "Meva-sabzavot"),
    "uzum": ("kg", "Meva-sabzavot"),
    "shaftoli": ("kg", "Meva-sabzavot"),
    "piyoz": ("kg", "Meva-sabzavot"),
    "kartoshka": ("kg", "Meva-sabzavot"),
    "shakar": ("kg", "Quruq oziq-ovqat"),
    "tuz": ("kg", "Quruq oziq-ovqat"),
    "non": ("dona", "Non & bakery"),
    "shokolad": ("dona", "Shirinliklar"),
    "suv": ("litr", "Ichimliklar"),
    "sut": ("karobka", "Sut mahsulotlari"),
}

PLAN_COLS = ["item", "category", "unit", "plan_qty"]
BUY_COLS = PLAN_COLS + ["bought", "actual_qty", "unit_price_gross", "line_gross", "line_net", "line_vat"]

@st.cache_data(show_spinner=False)
def example_plan_df():
    rows = []
    for name, (unit, cat) in COMMON_ITEMS.items():
        rows.append({
            "item": name.title(),
            "category": cat,
            "unit": unit,
            "plan_qty": 1.0 if unit in UNITS_FLOAT else 1,
        })
    return pd.DataFrame(rows, columns=PLAN_COLS)

# --- State init ---
if "plan_df" not in st.session_state:
    st.session_state.plan_df = example_plan_df()
if "buy_df" not in st.session_state:
    df = st.session_state.plan_df.copy()
    for c in ["bought", "actual_qty", "unit_price_gross", "line_gross", "line_net", "line_vat"]:
        df[c] = 0
    df["bought"] = False
    st.session_state.buy_df = df[BUY_COLS].copy()
if "qqs_rate" not in st.session_state:
    st.session_state.qqs_rate = DEFAULT_QQS

# --- Utils ---
def fmt_money(x: float) -> str:
    try:
        return f"{int(round(float(x))):,}".replace(",", " ") + " so'm"
    except Exception:
        return "—"

def coerce_qty(val, unit: str):
    if pd.isna(val) or val == "":
        return 0
    try:
        if unit in UNITS_FLOAT:
            v = float(val)
            return max(0.0, round(v, 3))
        else:
            v = int(float(val))
            return max(0, v)
    except Exception:
        return 0

def split_vat_from_gross(gross: float, rate_percent: float):
    r = float(rate_percent)
    if gross <= 0 or r < 0:
        return 0.0, 0.0
    vat = gross * (r / (100.0 + r))
    net = gross - vat
    return net, vat

def recompute_buy_df(df: pd.DataFrame, qqs_rate: float) -> pd.DataFrame:
    out = df.copy()
    for idx, row in out.iterrows():
        unit = row["unit"]
        out.at[idx, "plan_qty"] = coerce_qty(row["plan_qty"], unit)
        out.at[idx, "bought"] = bool(row.get("bought", False))
        out.at[idx, "actual_qty"] = coerce_qty(row.get("actual_qty", 0), unit)
        up = float(row.get("unit_price_gross", 0) or 0)
        out.at[idx, "unit_price_gross"] = max(0.0, up)

        line_gross = (out.at[idx, "actual_qty"] * up) if out.at[idx, "bought"] else 0.0
        net, vat = split_vat_from_gross(line_gross, qqs_rate)
        out.at[idx, "line_gross"] = line_gross
        out.at[idx, "line_net"] = net
        out.at[idx, "line_vat"] = vat
    return out

def df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")

def purchases_excel_bytes(buy_df: pd.DataFrame, summary_df: pd.DataFrame, cat_df: pd.DataFrame) -> bytes:
    # xlsxwriter kerak:  pip install XlsxWriter
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as xw:
        buy_df.to_excel(xw, sheet_name="Purchases", index=False)
        summary_df.to_excel(xw, sheet_name="Summary", index=False)
        cat_df.to_excel(xw, sheet_name="ByCategory", index=False)
    bio.seek(0)
    return bio.read()

# --- UI ---
st.title("🛒 Bozorlik — Reja → Xarid → Tahlil")
st.caption("Ro'yxat tuzing, bozorda narx va miqdorlarni kiriting, yakunda tahliliy xulosa oling.")

qqs_col1, qqs_col2 = st.columns([1, 6])
with qqs_col1:
    st.session_state.qqs_rate = st.number_input(
        "QQS %",
        min_value=0.0, max_value=100.0,
        value=float(st.session_state.qqs_rate),
        step=0.5,
        help="Narxlar QQS bilan. Chekda QQS ajratiladi."
    )
with qqs_col2:
    st.info("Narxlar QQS bilan kiritiladi. Hisobotda Net (QQSsiz), QQS va Gross alohida ko'rsatiladi.")

TAB1, TAB2, TAB3 = st.tabs(["1) Reja (oldindan ro'yxat)", "2) Bozorda (chek va narxlar)", "3) Tahlil (summary)"])

# --- TAB 1: Plan ---
with TAB1:
    st.subheader("1) Reja tuzish")
    st.write("Pastdagi formadan yoki tayyor ro'yxatdan foydalaning. So'ngra CSV sifatida saqlab qo'yishingiz mumkin.")

    with st.expander("➕ Tez qo'shish (tayyor mahsulotlar)"):
        c1, c2 = st.columns([2, 1])
        chosen = c1.selectbox("Mahsulot tanlang", options=[""] + sorted(COMMON_ITEMS.keys()))
        if chosen:
            unit, cat = COMMON_ITEMS[chosen]
        else:
            unit, cat = "kg", "Boshqa"
        plan_qty_default = 1.0 if unit in UNITS_FLOAT else 1
        qty = c2.number_input(
            "Reja miqdori",
            min_value=0.0,
            step=0.1 if unit in UNITS_FLOAT else 1.0,
            value=float(plan_qty_default),
            format="%.3f" if unit in UNITS_FLOAT else "%.0f",   # ✅ Streamlit NumberColumn formatiga mos
        )
        unit_sel = st.selectbox("Birlik", options=ALL_UNITS, index=ALL_UNITS.index(unit))
        cat_sel = st.selectbox("Kategoriya", options=DEFAULT_CATEGORIES,
                               index=DEFAULT_CATEGORIES.index(cat) if cat in DEFAULT_CATEGORIES else DEFAULT_CATEGORIES.index("Boshqa"))
        display_name = chosen.title() if chosen else st.text_input("Yangi mahsulot nomi", value="")
        add_ok = st.button("🔹 Rejaga qo'shish")
        if add_ok and display_name.strip():
            new_row = {
                "item": display_name.strip(),
                "category": cat_sel,
                "unit": unit_sel,
                "plan_qty": qty if unit_sel in UNITS_FLOAT else int(qty),
            }
            st.session_state.plan_df = pd.concat(
                [st.session_state.plan_df, pd.DataFrame([new_row])],
                ignore_index=True
            )
            st.success(f"{display_name.strip()} reja ro'yxatiga qo'shildi")

    st.markdown("**Reja jadvali (tahrirlash mumkin):**")
    plan_editor = st.data_editor(
        st.session_state.plan_df,
        column_config={
            "item": st.column_config.TextColumn("Mahsulot"),
            "category": st.column_config.SelectboxColumn("Kategoriya", options=DEFAULT_CATEGORIES),
            "unit": st.column_config.SelectboxColumn("Birlik", options=ALL_UNITS),
            "plan_qty": st.column_config.NumberColumn("Reja miqdori", step=0.1, format="%.3f"),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="plan_editor",
    )
    st.session_state.plan_df = plan_editor[PLAN_COLS].copy()

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("🧹 Rejani tozalash"):
            st.session_state.plan_df = example_plan_df().head(0)
            st.success("Reja tozalandi")
    with c2:
        st.download_button("⬇️ Rejani CSV sifatida yuklab olish",
                           data=df_to_csv_bytes(st.session_state.plan_df),
                           file_name="bozorlik_reja.csv", mime="text/csv")
    with c3:
        up = st.file_uploader("Yoki CSV dan yuklash", type=["csv"], accept_multiple_files=False)
        if up is not None:
            try:
                df = pd.read_csv(up)
                # Normalize columns
                rename_map = {c: c.strip().lower() for c in df.columns}
                df.columns = [rename_map[c] for c in df.columns]
                miss = [c for c in ["item", "unit", "plan_qty"] if c not in df.columns]
                if miss:
                    st.error(f"CSV ustunlari yetarli emas. Kerak: item, unit, plan_qty (topilmadi: {', '.join(miss)}).")
                else:
                    if "category" not in df.columns:
                        df["category"] = "Boshqa"
                    st.session_state.plan_df = df[PLAN_COLS].copy()
                    st.success("Reja CSV dan yuklandi")
            except Exception as e:
                st.error(f"Yuklashda xatolik: {e}")

    if st.button("➡️ Bozorda sahifasini yangilash (rejadan)"):
        base = st.session_state.plan_df.copy()
        for c in ["bought", "actual_qty", "unit_price_gross", "line_gross", "line_net", "line_vat"]:
            base[c] = 0
        base["bought"] = False
        st.session_state.buy_df = base[BUY_COLS].copy()
        st.success("Bozorda jadvali reja asosida yangilandi")

# --- TAB 2: Buy ---
with TAB2:
    st.subheader("2) Bozorda — narx va chek")
    st.write("Quyida har bir mahsulot uchun: ✅ olindi, **miqdor** va **birlik narxi (Gross, QQS bilan)** kiriting. Pastda chek va jami hisob chiqadi.")

    buy_editor = st.data_editor(
        st.session_state.buy_df,
        column_config={
            "item": st.column_config.TextColumn("Mahsulot"),
            "category": st.column_config.SelectboxColumn("Kategoriya", options=DEFAULT_CATEGORIES),
            "unit": st.column_config.SelectboxColumn("Birlik", options=ALL_UNITS),
            "plan_qty": st.column_config.NumberColumn("Reja miqdori", step=0.1, format="%.3f"),
            "bought": st.column_config.CheckboxColumn("Olindi mi?"),
            "actual_qty": st.column_config.NumberColumn("Real miqdor", step=0.1, format="%.3f",
                                                        help="Olindi deb belgilansa hisobga olinadi"),
            "unit_price_gross": st.column_config.NumberColumn("Birlik narxi (Gross, QQS bilan)", step=100.0),
        },
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="buy_editor",
    )

    buy_df = recompute_buy_df(buy_editor[BUY_COLS], st.session_state.qqs_rate)
    st.session_state.buy_df = buy_df.copy()

    cek = buy_df[buy_df["bought"]].copy()
    cols_show = ["item", "category", "unit", "actual_qty", "unit_price_gross", "line_net", "line_vat", "line_gross"]
    st.markdown("**🧾 Chek (olinganlar):**")
    st.dataframe(cek[cols_show], use_container_width=True)

    gross_total = float(cek["line_gross"].sum())
    net_total, vat_total = split_vat_from_gross(gross_total, st.session_state.qqs_rate)

    m1, m2, m3 = st.columns(3)
    m1.metric("Jami Net (QQSsiz)", fmt_money(net_total))
    m2.metric("Jami QQS", fmt_money(vat_total))
    m3.metric("Jami Gross (QQS bilan)", fmt_money(gross_total))

    st.download_button(
        "⬇️ Chek (CSV)",
        data=df_to_csv_bytes(cek[cols_show]),
        file_name="bozorlik_chek.csv",
        mime="text/csv",
    )

# --- TAB 3: Summary ---
with TAB3:
    st.subheader("3) Tahlil — kategoriyalar bo'yicha")

    fakt = st.session_state.buy_df.copy()
    fakt = fakt[fakt["bought"]].copy()

    rvf = st.session_state.buy_df[["item", "category", "unit", "plan_qty", "bought", "actual_qty", "line_gross", "line_net", "line_vat"]].copy()
    rvf["qty_diff"] = rvf["actual_qty"] - rvf["plan_qty"]
    st.markdown("**Reja vs Fakt (miqdor):**")
    st.dataframe(rvf, use_container_width=True)

    if not fakt.empty:
        cat = (
            fakt.groupby("category", as_index=False)
                .agg(
                    items=("item", "count"),
                    qty=("actual_qty", "sum"),
                    net=("line_net", "sum"),
                    qqs=("line_vat", "sum"),
                    gross=("line_gross", "sum"),
                )
                .sort_values("gross", ascending=False)
        )

        st.markdown("**Kategoriya bo'yicha sarf (Net/QQS/Gross):**")
        st.dataframe(cat, use_container_width=True)

        summary = pd.DataFrame([
            {"metric": "Jami Net (QQSsiz)", "value": float(fakt["line_net"].sum())},
            {"metric": "Jami QQS", "value": float(fakt["line_vat"].sum())},
            {"metric": "Jami Gross (QQS bilan)", "value": float(fakt["line_gross"].sum())},
            {"metric": "Umumiy pozitsiyalar (olingan)", "value": int(fakt.shape[0])},
        ])
        st.markdown("**Umumiy ko'rsatkichlar:**")
        st.dataframe(summary, use_container_width=True)

        if ALTAIR_OK and not cat.empty:
            st.markdown("**Kategoriya bo'yicha Gross (diagramma):**")
            ch1 = alt.Chart(cat).mark_arc().encode(
                theta="gross", color="category",
                tooltip=["category", "gross", "net", "qqs", "qty"]
            )
            st.altair_chart(ch1, use_container_width=True)

            st.markdown("**Mahsulotlar bo'yicha birlik narxlar (Gross):**")
            prod = fakt[["item", "unit", "unit_price_gross", "line_gross"]].copy().sort_values("unit_price_gross", ascending=False)
            ch2 = alt.Chart(prod).mark_bar().encode(
                x=alt.X("item:N", sort="-y"),
                y="unit_price_gross:Q",
                tooltip=["item", "unit", "unit_price_gross"]
            )
            st.altair_chart(ch2, use_container_width=True)

        excel_bytes = purchases_excel_bytes(
            buy_df=st.session_state.buy_df,
            summary_df=summary,
            cat_df=cat,
        )
        st.download_button(
            "⬇️ Hisobot (Excel, 3 ta varaq)",
            data=excel_bytes,
            file_name="bozorlik_hisobot.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Hali xarid kiritilmadi (olinganlar yo'q)")

st.markdown("---")
st.caption("© Bozorlik ilovasi — reja, chek va tahlil bitta joyda. QQS avtomatik ajratiladi.")
