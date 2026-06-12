"""
Dashboard - Sondage HPV (Virus du Papillome Humain)
استبيان فيروس الورم الحليمي البشري

Comment lancer :
    pip install streamlit pandas plotly gspread google-auth openpyxl
    streamlit run dashboard_hpv.py

Comment connecter Google Sheets :
    - Voir le README en bas du fichier ou le fichier GOOGLE_SHEETS_SETUP.md
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import StringIO
import json

# ─────────────────────────────────────────────
#  CONFIG PAGE
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard – Sondage HPV",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  PALETTE & STYLE
# ─────────────────────────────────────────────
COLORS = {
    "primary":   "#6C5CE7",
    "secondary": "#00CEC9",
    "accent":    "#FD79A8",
    "warning":   "#FDCB6E",
    "success":   "#00B894",
    "dark":      "#2D3436",
    "light":     "#F8F9FA",
}
COLOR_SEQ = [
    "#6C5CE7", "#00CEC9", "#FD79A8", "#FDCB6E",
    "#00B894", "#E17055", "#74B9FF", "#A29BFE",
]

st.markdown("""
<style>
    .stMetric { background: #f8f9fa; border-radius: 12px; padding: 12px; }
    .section-title {
        font-size: 1.3rem; font-weight: 700;
        color: #6C5CE7; border-left: 4px solid #6C5CE7;
        padding-left: 10px; margin-top: 2rem; margin-bottom: 1rem;
    }
    .insight-box {
        background: linear-gradient(135deg, #f0eeff 0%, #e8f8f8 100%);
        border-radius: 10px; padding: 14px 18px; margin: 8px 0;
        border-left: 4px solid #6C5CE7;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
#  COLUMN MAPPING  (short names used in code)
# ─────────────────────────────────────────────
COL = {
    "genre":          "1. الجنس",
    "age":            "2. الفئة العمرية",
    "education":      "3. المستوى التعليمي",
    "children":       "4. هل لديك أبناء في الفئة العمرية بين 9 و18 عامًا؟",
    "heard_hpv":      "5. هل سبق أن سمعت بفيروس الورم الحليمي البشري (HPV)؟",
    "hpv_what":       "6. ما هو فيروس HPV في نظرك؟",
    "hpv_cancer":     "7. هل تعلم أن فيروس HPV هو السبب الرئيسي لسرطان عنق الرحم؟",
    "transmission":   "8. كيف يُنتقل فيروس HPV؟",
    "vaccine_exists": "9. هل تعلم بوجود لقاح يقي من هذا الفيروس؟",
    "info_source":    "10. من أين تلقيت معلوماتك حول HPV أو لقاحه؟",
    "myths":          "11. أي من العبارات التالية سمعت عنها؟",
    "state_trust":    "12. ما مدى ثقتك في سلامة اللقاحات التي توفرها الدولة؟",
    "barriers":       "13. ما أبرز الأسباب التي قد تمنعك من قبول لقاح HPV أو التردد بشأنه؟",
    "best_channel":   "14. ما القناة الأكثر تأثيرًا لتصحيح المعلومات الخاطئة حول اللقاح؟",
    "tr_doctor":      "15. ما مدى ثقتك في المصادر التالية؟ [طبيب أو ممرض/ة]",
    "tr_school":      "15. ما مدى ثقتك في المصادر التالية؟ [المدرسة أو الجامعة]",
    "tr_media":       "15. ما مدى ثقتك في المصادر التالية؟ [وسائل الإعلام الرسمية]",
    "tr_social":      "15. ما مدى ثقتك في المصادر التالية؟ [وسائل التواصل الاجتماعي]",
    "tr_family":      "15. ما مدى ثقتك في المصادر التالية؟ [العائلة أو الأصدقاء]",
    "tr_ngo":         "15. ما مدى ثقتك في المصادر التالية؟ [الجمعيات والمنظمات المحلية]",
    "vaccine_offered":"18. هل عُرض على طفلتك اللقاح في إطار البرنامج الوطني؟",
    "refuse_reason":  "19. إذا رفضت أو ترددت، ما السبب الرئيسي؟",
    "reconsider":     "20. هل ستعيد النظر في قرارك إذا حصلت على معلومات موثوقة من طبيب مختص؟",
}

TRUST_ORDER = ["1 لا أثق", "2", "2.0", "3", "3.0", "4", "4.0", "5 ثقة تامة"]

def trust_score(val):
    """Convert trust string to numeric 1-5."""
    if pd.isna(val): return None
    v = str(val).strip()
    if v.startswith("1"): return 1
    if v.startswith("5"): return 5
    try: return int(float(v))
    except: return None

# ─────────────────────────────────────────────
#  DATA LOADING
# ─────────────────────────────────────────────
@st.cache_data(ttl=300)
def load_google_sheets(sheet_url: str) -> pd.DataFrame:
    """Load data directly from a public Google Sheets URL."""
    # Convert share URL to CSV export URL
    if "spreadsheets/d/" in sheet_url:
        sheet_id = sheet_url.split("spreadsheets/d/")[1].split("/")[0]
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        df = pd.read_csv(csv_url)
        return df
    raise ValueError("URL Google Sheets invalide")

@st.cache_data(ttl=300)
def load_google_sheets_service_account(sheet_id: str, creds_json: str) -> pd.DataFrame:
    """Load from Google Sheets using a service account (for private sheets)."""
    import gspread
    from google.oauth2.service_account import Credentials
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"]
    )
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    return pd.DataFrame(data)

def load_excel(file) -> pd.DataFrame:
    return pd.read_excel(file, engine="openpyxl")

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def explode_multi(df, col):
    """Explode a column with comma-separated multiple-choice answers."""
    if col not in df.columns: return pd.Series(dtype=str)
    s = df[col].dropna().str.split(",").explode().str.strip()
    return s[s != ""].value_counts()

def pie_chart(series, title, height=320):
    fig = px.pie(
        values=series.values, names=series.index,
        title=title, color_discrete_sequence=COLOR_SEQ, hole=0.4,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(height=height, margin=dict(t=40, b=10, l=10, r=10),
                      showlegend=False)
    return fig

def bar_chart(series, title, height=350, horizontal=False):
    s = series.sort_values(ascending=True if horizontal else False)
    if horizontal:
        fig = px.bar(x=s.values, y=s.index, orientation="h",
                     title=title, color=s.index,
                     color_discrete_sequence=COLOR_SEQ)
    else:
        fig = px.bar(x=s.index, y=s.values,
                     title=title, color=s.index,
                     color_discrete_sequence=COLOR_SEQ)
    fig.update_layout(height=height, showlegend=False,
                      margin=dict(t=40, b=10, l=10, r=10),
                      xaxis_tickangle=-30 if not horizontal else 0)
    return fig

def kpi(label, value, delta=None, color="#6C5CE7"):
    st.metric(label=label, value=value, delta=delta)

# ─────────────────────────────────────────────
#  SIDEBAR — DATA SOURCE
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Papilloma_Virus_%28HPV%29_EM.jpg/220px-Papilloma_Virus_%28HPV%29_EM.jpg", width=120)
    st.title("⚙️ Source de données")

    source = st.radio(
        "Choisir la source :",
        ["📊 Google Sheets (public)", "🔑 Google Sheets (privé)", "📁 Fichier Excel/CSV"],
        index=0,
    )

    df = None

    if source == "📊 Google Sheets (public)":
        st.info("Rends ta Google Sheet publique :\nFichier → Partager → Tout le monde avec le lien → Lecteur")
        url = st.text_input(
            "URL Google Sheets",
            placeholder="https://docs.google.com/spreadsheets/d/...",
        )
        if url:
            with st.spinner("Chargement..."):
                try:
                    df = load_google_sheets(url)
                    st.success(f"✅ {len(df)} réponses chargées")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    elif source == "🔑 Google Sheets (privé)":
        st.info("Nécessite un fichier JSON de compte de service Google.")
        sheet_id = st.text_input("ID de la feuille (partie de l'URL)")
        creds_file = st.file_uploader("Fichier credentials.json", type="json")
        if sheet_id and creds_file:
            with st.spinner("Connexion..."):
                try:
                    df = load_google_sheets_service_account(sheet_id, creds_file.read().decode())
                    st.success(f"✅ {len(df)} réponses chargées")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    else:  # Excel / CSV
        uploaded = st.file_uploader("Déposer un fichier", type=["xlsx", "xls", "csv"])
        if uploaded:
            try:
                if uploaded.name.endswith(".csv"):
                    df = pd.read_csv(uploaded)
                else:
                    df = pd.read_excel(uploaded, engine="openpyxl")
                st.success(f"✅ {len(df)} réponses chargées")
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.markdown("---")
    if df is not None:
        st.markdown(f"**Réponses totales :** `{len(df)}`")
        st.markdown(f"**Colonnes :** `{len(df.columns)}`")

        # ── Filtres
        st.subheader("🔍 Filtres")

        genres = ["Tous"] + sorted(df[COL["genre"]].dropna().unique().tolist()) if COL["genre"] in df.columns else ["Tous"]
        ages   = ["Tous"] + sorted(df[COL["age"]].dropna().unique().tolist()) if COL["age"] in df.columns else ["Tous"]
        edus   = ["Tous"] + sorted(df[COL["education"]].dropna().unique().tolist()) if COL["education"] in df.columns else ["Tous"]

        f_genre = st.selectbox("Genre", genres)
        f_age   = st.selectbox("Tranche d'âge", ages)
        f_edu   = st.selectbox("Niveau d'études", edus)

        def apply_filters(d):
            if f_genre != "Tous" and COL["genre"] in d.columns:
                d = d[d[COL["genre"]] == f_genre]
            if f_age != "Tous" and COL["age"] in d.columns:
                d = d[d[COL["age"]] == f_age]
            if f_edu != "Tous" and COL["education"] in d.columns:
                d = d[d[COL["education"]] == f_edu]
            return d

        df = apply_filters(df)
        st.markdown(f"**Après filtres :** `{len(df)}`")

# ─────────────────────────────────────────────
#  MAIN CONTENT
# ─────────────────────────────────────────────
st.markdown("# 🔬 Dashboard — Sondage HPV")
st.markdown("**استبيان مجهول حول فيروس الورم الحليمي البشري ولقاحه**")
st.markdown("---")

if df is None:
    st.info("👈 Commence par choisir une source de données dans la barre latérale.")
    st.stop()

n = len(df)

# ══════════════════════════════════════════
#  SECTION 1 — KPIs globaux
# ══════════════════════════════════════════
st.markdown('<div class="section-title">📌 Vue d\'ensemble</div>', unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi("👥 Réponses totales", n)
with c2:
    if COL["heard_hpv"] in df.columns:
        pct = round(df[df[COL["heard_hpv"]] == "نعم"].shape[0] / n * 100, 1)
        kpi("💡 Connaissent HPV", f"{pct}%")
with c3:
    if COL["vaccine_exists"] in df.columns:
        pct2 = round(df[df[COL["vaccine_exists"]] == "نعم"].shape[0] / n * 100, 1)
        kpi("💉 Savent qu'un vaccin existe", f"{pct2}%")
with c4:
    if COL["hpv_cancer"] in df.columns:
        pct3 = round(df[df[COL["hpv_cancer"]] == "نعم"].shape[0] / n * 100, 1)
        kpi("🎗️ HPV → Cancer col utérus", f"{pct3}%")
with c5:
    if COL["genre"] in df.columns:
        pct_f = round(df[df[COL["genre"]] == "أنثى"].shape[0] / n * 100, 1)
        kpi("♀️ % Femmes", f"{pct_f}%")

# ══════════════════════════════════════════
#  SECTION 2 — Démographie
# ══════════════════════════════════════════
st.markdown('<div class="section-title">👤 1. Informations démographiques — المعلومات الديموغرافية</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if COL["genre"] in df.columns:
        s = df[COL["genre"]].value_counts()
        st.plotly_chart(pie_chart(s, "Genre — الجنس"), use_container_width=True)

with col2:
    if COL["age"] in df.columns:
        age_order = ["أقل من 18 عامًا", "18–25 عامًا", "26–40 عامًا", "41–60 عامًا", "أكثر من 60 عامًا"]
        s = df[COL["age"]].value_counts().reindex([a for a in age_order if a in df[COL["age"]].unique()])
        fig = px.bar(x=s.index, y=s.values, title="Tranche d'âge — الفئة العمرية",
                     color=s.index, color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(height=320, showlegend=False, xaxis_tickangle=-20,
                          margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with col3:
    if COL["education"] in df.columns:
        s = df[COL["education"]].value_counts()
        st.plotly_chart(pie_chart(s, "Niveau d'études — المستوى التعليمي"), use_container_width=True)

if COL["children"] in df.columns:
    s = df[COL["children"]].value_counts()
    st.plotly_chart(bar_chart(s, "Enfants entre 9 et 18 ans — هل لديك أبناء في الفئة العمرية بين 9 و18 عامًا؟", horizontal=True), use_container_width=True)

# ══════════════════════════════════════════
#  SECTION 3 — Connaissance HPV & Vaccin
# ══════════════════════════════════════════
st.markdown('<div class="section-title">📚 2. Connaissance HPV & Vaccin — المعرفة بفيروس HPV واللقاح</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    if COL["heard_hpv"] in df.columns:
        s = df[COL["heard_hpv"]].value_counts()
        st.plotly_chart(pie_chart(s, "Déjà entendu parler de HPV ?\nهل سبق أن سمعت بـ HPV؟"), use_container_width=True)

with col2:
    if COL["vaccine_exists"] in df.columns:
        s = df[COL["vaccine_exists"]].value_counts()
        st.plotly_chart(pie_chart(s, "Savent qu'un vaccin existe ?\nهل تعلم بوجود لقاح؟"), use_container_width=True)

with col3:
    if COL["hpv_cancer"] in df.columns:
        s = df[COL["hpv_cancer"]].value_counts()
        st.plotly_chart(pie_chart(s, "HPV = cause principale cancer col ?\nهل تعلم أن HPV هو السبب الرئيسي لسرطان عنق الرحم؟"), use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    if COL["hpv_what"] in df.columns:
        s = df[COL["hpv_what"]].value_counts()
        st.plotly_chart(bar_chart(s, "Qu'est-ce que HPV selon vous ?\nما هو فيروس HPV في نظرك؟", horizontal=True), use_container_width=True)

with col2:
    if COL["transmission"] in df.columns:
        s = explode_multi(df, COL["transmission"])
        st.plotly_chart(bar_chart(s, "Comment HPV se transmet ?\nكيف يُنتقل فيروس HPV؟", horizontal=True), use_container_width=True)

if COL["info_source"] in df.columns:
    s = explode_multi(df, COL["info_source"])
    st.plotly_chart(bar_chart(s, "Source d'information sur HPV/vaccin — من أين تلقيت معلوماتك؟", horizontal=True, height=380), use_container_width=True)

# ══════════════════════════════════════════
#  SECTION 4 — Croyances & Obstacles
# ══════════════════════════════════════════
st.markdown('<div class="section-title">🧠 3. Croyances & Obstacles — المعتقدات والعوائق</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    if COL["myths"] in df.columns:
        s = explode_multi(df, COL["myths"])
        st.plotly_chart(bar_chart(s, "Rumeurs entendues — أي من العبارات التالية سمعت عنها؟", horizontal=True, height=400), use_container_width=True)

with col2:
    if COL["barriers"] in df.columns:
        s = explode_multi(df, COL["barriers"])
        st.plotly_chart(bar_chart(s, "Obstacles à l'acceptation du vaccin — ما أبرز الأسباب التي قد تمنعك؟", horizontal=True, height=400), use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    if COL["state_trust"] in df.columns:
        trust_order = ["ثقة تامة", "ثقة نسبية", "لست متأكدًا", "ثقة ضعيفة", "لا ثقة على الإطلاق"]
        s = df[COL["state_trust"]].value_counts().reindex([t for t in trust_order if t in df[COL["state_trust"]].unique()])
        colors_trust = ["#00B894", "#00CEC9", "#FDCB6E", "#E17055", "#D63031"]
        fig = px.bar(x=s.index, y=s.values,
                     title="Confiance dans les vaccins de l'État — ما مدى ثقتك في سلامة اللقاحات التي توفرها الدولة؟",
                     color=s.index, color_discrete_sequence=colors_trust)
        fig.update_layout(height=350, showlegend=False, xaxis_tickangle=-20,
                          margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if COL["best_channel"] in df.columns:
        s = df[COL["best_channel"]].value_counts()
        st.plotly_chart(bar_chart(s, "Canal le + efficace pour corriger les idées reçues\nما القناة الأكثر تأثيرًا؟", horizontal=True), use_container_width=True)

# ══════════════════════════════════════════
#  SECTION 5 — Confiance dans les sources
# ══════════════════════════════════════════
st.markdown('<div class="section-title">🤝 4. Confiance dans les sources — الثقة في مصادر المعلومات</div>', unsafe_allow_html=True)

trust_cols = {
    "Médecin/infirmier\nطبيب أو ممرض/ة":         COL["tr_doctor"],
    "École/Université\nالمدرسة أو الجامعة":       COL["tr_school"],
    "Médias officiels\nوسائل الإعلام الرسمية":    COL["tr_media"],
    "Réseaux sociaux\nوسائل التواصل الاجتماعي":   COL["tr_social"],
    "Famille/Amis\nالعائلة أو الأصدقاء":          COL["tr_family"],
    "Associations locales\nالجمعيات والمنظمات":   COL["tr_ngo"],
}

scores = {}
for label, col in trust_cols.items():
    if col in df.columns:
        vals = df[col].apply(trust_score).dropna()
        if len(vals):
            scores[label.split("\n")[0]] = round(vals.mean(), 2)

if scores:
    fig = go.Figure(go.Bar(
        x=list(scores.values()),
        y=list(scores.keys()),
        orientation="h",
        marker_color=COLOR_SEQ[:len(scores)],
        text=[f"{v}/5" for v in scores.values()],
        textposition="outside",
    ))
    fig.update_layout(
        title="Score moyen de confiance par source (sur 5) — متوسط الثقة لكل مصدر",
        height=380, xaxis_range=[0, 5.5],
        margin=dict(t=50, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Radar chart
    categories = list(scores.keys())
    vals_list  = list(scores.values())
    fig_radar = go.Figure(go.Scatterpolar(
        r=vals_list + [vals_list[0]],
        theta=categories + [categories[0]],
        fill="toself",
        line_color=COLORS["primary"],
        fillcolor="rgba(108,92,231,0.2)",
    ))
    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
        title="Radar — Confiance par source",
        height=420,
    )
    st.plotly_chart(fig_radar, use_container_width=True)

# ══════════════════════════════════════════
#  SECTION 6 — Parents uniquement
# ══════════════════════════════════════════
st.markdown('<div class="section-title">👨‍👩‍👧 6. Questions parents — أسئلة خاصة بأولياء الأمور</div>', unsafe_allow_html=True)

has_parents = COL["vaccine_offered"] in df.columns and df[COL["vaccine_offered"]].notna().sum() > 0
if has_parents:
    df_parents = df[df[COL["vaccine_offered"]].notna() & (df[COL["vaccine_offered"]] != "لا ينطبق")]
    if len(df_parents) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            s = df_parents[COL["vaccine_offered"]].value_counts()
            st.plotly_chart(pie_chart(s, "Vaccin proposé à l'enfant ?\nهل عُرض على طفلتك اللقاح؟"), use_container_width=True)
        with col2:
            if COL["refuse_reason"] in df.columns:
                df_refuse = df_parents[df_parents[COL["refuse_reason"]].notna() & (df_parents[COL["refuse_reason"]] != "لا ينطبق")]
                if len(df_refuse):
                    s = df_refuse[COL["refuse_reason"]].value_counts()
                    st.plotly_chart(bar_chart(s, "Raison du refus/hésitation\nإذا رفضت، ما السبب؟", horizontal=True), use_container_width=True)
        with col3:
            if COL["reconsider"] in df.columns:
                df_rc = df_parents[df_parents[COL["reconsider"]].notna() & (df_parents[COL["reconsider"]] != "لا ينطبق")]
                if len(df_rc):
                    s = df_rc[COL["reconsider"]].value_counts()
                    st.plotly_chart(pie_chart(s, "Reconsidération possible ?\nهل ستعيد النظر في قرارك؟"), use_container_width=True)
    else:
        st.info("Aucune réponse parent dans les données filtrées.")

# ══════════════════════════════════════════
#  SECTION 7 — Analyses croisées
# ══════════════════════════════════════════
st.markdown('<div class="section-title">🔗 Analyses croisées — تحليلات متقاطعة</div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    # Genre × Connaissance HPV
    if COL["genre"] in df.columns and COL["heard_hpv"] in df.columns:
        ct = pd.crosstab(df[COL["genre"]], df[COL["heard_hpv"]])
        ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
        fig = px.bar(ct_pct, barmode="group",
                     title="Genre × Connaissance HPV (%) — الجنس × معرفة HPV",
                     color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(height=350, margin=dict(t=50, b=10, l=10, r=10), yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

with col2:
    # Niveau d'études × Connaissance vaccin
    if COL["education"] in df.columns and COL["vaccine_exists"] in df.columns:
        ct = pd.crosstab(df[COL["education"]], df[COL["vaccine_exists"]])
        ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
        fig = px.bar(ct_pct, barmode="group",
                     title="Niveau d'études × Connaissance vaccin (%) — المستوى × معرفة اللقاح",
                     color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(height=350, margin=dict(t=50, b=10, l=10, r=10),
                          xaxis_tickangle=-20, yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)

with col1:
    # Âge × Confiance État
    if COL["age"] in df.columns and COL["state_trust"] in df.columns:
        ct = pd.crosstab(df[COL["age"]], df[COL["state_trust"]])
        ct_pct = ct.div(ct.sum(axis=1), axis=0) * 100
        fig = px.imshow(ct_pct, text_auto=".0f",
                        title="Âge × Confiance vaccins État (%) — الفئة العمرية × الثقة بلقاحات الدولة",
                        color_continuous_scale="Purples")
        fig.update_layout(height=380, margin=dict(t=50, b=10, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    # Genre × Confiance moyenne dans les sources
    if COL["genre"] in df.columns and COL["tr_doctor"] in df.columns:
        res = []
        for label, col in trust_cols.items():
            if col in df.columns:
                grp = df.groupby(COL["genre"])[col].apply(
                    lambda x: x.apply(trust_score).mean()
                ).reset_index()
                grp.columns = ["Genre", "Score moyen"]
                grp["Source"] = label.split("\n")[0]
                res.append(grp)
        if res:
            df_trust = pd.concat(res)
            fig = px.bar(df_trust, x="Source", y="Score moyen", color="Genre",
                         barmode="group",
                         title="Confiance moyenne par source et par genre\nمتوسط الثقة حسب المصدر والجنس",
                         color_discrete_sequence=COLOR_SEQ)
            fig.update_layout(height=380, xaxis_tickangle=-20,
                               margin=dict(t=60, b=10, l=10, r=10))
            st.plotly_chart(fig, use_container_width=True)

# ══════════════════════════════════════════
#  SECTION 8 — Insights clés
# ══════════════════════════════════════════
st.markdown('<div class="section-title">💡 Insights clés — أبرز النتائج</div>', unsafe_allow_html=True)

insights = []

if COL["heard_hpv"] in df.columns:
    pct_know = df[df[COL["heard_hpv"]] == "نعم"].shape[0] / n * 100
    insights.append(f"🔵 <b>{pct_know:.0f}%</b> des participants ont déjà entendu parler de HPV.")

if COL["vaccine_exists"] in df.columns:
    pct_vax = df[df[COL["vaccine_exists"]] == "نعم"].shape[0] / n * 100
    insights.append(f"💉 <b>{pct_vax:.0f}%</b> savent qu'un vaccin contre HPV existe.")

if COL["state_trust"] in df.columns:
    no_trust = df[df[COL["state_trust"]].isin(["ثقة ضعيفة", "لا ثقة على الإطلاق"])].shape[0] / n * 100
    insights.append(f"⚠️ <b>{no_trust:.0f}%</b> ont une confiance faible ou nulle dans les vaccins de l'État.")

if COL["barriers"] in df.columns:
    top_barrier = explode_multi(df, COL["barriers"]).index[0] if len(explode_multi(df, COL["barriers"])) else "N/A"
    insights.append(f"🚧 Principal obstacle : <b>{top_barrier}</b>")

if COL["best_channel"] in df.columns:
    top_channel = df[COL["best_channel"]].value_counts().index[0] if df[COL["best_channel"]].notna().sum() > 0 else "N/A"
    insights.append(f"📢 Canal préféré pour l'information correcte : <b>{top_channel}</b>")

for ins in insights:
    st.markdown(f'<div class="insight-box">{ins}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════
st.markdown("---")
st.markdown(
    "<center><small>Dashboard réalisé avec Streamlit & Plotly · "
    "استبيان مجهول حول فيروس الورم الحليمي البشري</small></center>",
    unsafe_allow_html=True
)