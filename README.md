# Bozorlik
Kundalik reja asosida qilinadigan bozorlik uchun mahsus web yordamchi.
# 🛒 Bozorlik — Reja → Xarid → Tahlil (Streamlit)

Bozorga borishdan oldin ro'yxat tuzing, bozorda real miqdor va narxlarni kiriting, yakunda **kategoriya bo‘yicha tahlil** (Net/QQS/Gross) oling. QQS avtomatik ajratiladi.  

**Tech:** Streamlit, Pandas, (ixtiyoriy) Altair, XlsxWriter

## ✨ Xususiyatlar
- **Reja**: mahsulot, birlik (kg/litr/dona/karobka), kategoriya, reja miqdori.
- **Chek**: bozorda olinganlar uchun miqdor va birlik narx (Gross, QQS bilan), Net/QQS ajratish.
- **Tahlil**: kategoriya kesimida sarf (Net/QQS/Gross), reja vs fakt, pie/bar grafiklar.
- **Eksport**: Chek (CSV), to‘liq hisobot (Excel, 3 varaq).
- QQS stavkasi sozlanadi (standart: 12%).

## 🚀 Tez boshlash
```bash
# 1) Klonlash
git clone https://github.com/<user>/bozorlik-app.git
cd bozorlik-app

# 2) Muhit (ixtiyoriy, lekin tavsiya)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3) Kutubxonalar
pip install -r requirements.txt

# 4) Ishga tushirish
streamlit run app_bozorlik.py
