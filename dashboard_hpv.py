"""
Dashboard - Sondage HPV  (version compacte)
Lancer : streamlit run dashboard_hpv.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json

# ── Page config ──────────────────────────────
st.set_page_config(
    page_title="Sondage HPV",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

COLOR_SEQ = ["#6C5CE7","#00CEC9","#FD79A8","#FDCB6E","#00B894","#E17055","#74B9FF","#A29BFE"]

st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #f4f1ff;
    border-radius: 14px;
    padding: 16px;
    border-left: 4px solid #6C5CE7;
}
.block-title {
    font-size: 1.15rem; font-weight: 700; color: #6C5CE7;
    border-left: 4px solid #6C5CE7; padding-left: 10px;
    margin: 1.5rem 0 0.8rem 0;
}
.insight {
    background: #f4f1ff; border-radius: 10px;
    padding: 12px 16px; margin: 6px 0;
    border-left: 4px solid #6C5CE7; font-size: 1rem;
}
</style>
""", unsafe_allow_html=True)

# ── Colonnes ─────────────────────────────────
COL = {
    "genre":       "1. الجنس",
    "age":         "2. الفئة العمرية",
    "education":   "3. المستوى التعليمي",
    "heard_hpv":   "5. هل سبق أن سمعت بفيروس الورم الحليمي البشري (HPV)؟",
    "hpv_cancer":  "7. هل تعلم أن فيروس HPV هو السبب الرئيسي لسرطان عنق الرحم؟",
    "vaccine_exists": "9. هل تعلم بوجود لقاح يقي من هذا الفيروس؟",
    "state_trust": "12. ما مدى ثقتك في سلامة اللقاحات التي توفرها الدولة؟",
    "barriers":    "13. ما أبرز الأسباب التي قد تمنعك من قبول لقاح HPV أو التردد بشأنه؟",
    "best_channel":"14. ما القناة الأكثر تأثيرًا لتصحيح المعلومات الخاطئة حول اللقاح؟",
    "myths":       "11. أي من العبارات التالية سمعت عنها؟",
}

def explode_multi(df, col):
    if col not in df.columns: return pd.Series(dtype=str)
    s = df[col].dropna().str.split(",").explode().str.strip()
    return s[s != ""].value_counts()

# ── Sidebar — source de données ──────────────
with st.sidebar:
    st.title("⚙️ Source de données")
    source = st.radio("", ["📊 Google Sheets (public)", "📁 Fichier Excel/CSV"])

    df = None

    if source == "📊 Google Sheets (public)":
        st.info("Fichier → Partager → Tout le monde avec le lien → Lecteur")
        url = st.text_input("URL Google Sheets", placeholder="https://docs.google.com/spreadsheets/d/...")
        if url:
            with st.spinner("Chargement..."):
                try:
                    sheet_id = url.split("spreadsheets/d/")[1].split("/")[0]
                    csv_url  = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                    df = pd.read_csv(csv_url)
                    st.success(f"✅ {len(df)} réponses chargées")
                except Exception as e:
                    st.error(f"Erreur : {e}")
    else:
        uploaded = st.file_uploader("Déposer un fichier", type=["xlsx","xls","csv"])
        if uploaded:
            try:
                df = pd.read_csv(uploaded) if uploaded.name.endswith(".csv") else pd.read_excel(uploaded, engine="openpyxl")
                st.success(f"✅ {len(df)} réponses chargées")
            except Exception as e:
                st.error(f"Erreur : {e}")

    if df is not None:
        st.markdown("---")
        st.subheader("🔍 Filtres")
        genres = ["Tous"] + sorted(df[COL["genre"]].dropna().unique().tolist()) if COL["genre"] in df.columns else ["Tous"]
        ages   = ["Tous"] + sorted(df[COL["age"]].dropna().unique().tolist())   if COL["age"]   in df.columns else ["Tous"]
        f_genre = st.selectbox("Genre", genres)
        f_age   = st.selectbox("Tranche d'âge", ages)
        if f_genre != "Tous" and COL["genre"] in df.columns: df = df[df[COL["genre"]] == f_genre]
        if f_age   != "Tous" and COL["age"]   in df.columns: df = df[df[COL["age"]]   == f_age]
        st.markdown(f"**Réponses :** `{len(df)}`")

# ── Main ─────────────────────────────────────
st.markdown("# 🔬 Sondage HPV — Résultats")
st.markdown("**استبيان مجهول حول فيروس الورم الحليمي البشري ولقاحه**")
st.markdown("---")

if df is None:
    st.info("👈 Connecte ta source de données dans la barre latérale.")
    st.stop()

n = len(df)

# ── KPIs ─────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1: st.metric("👥 Participants", n)
with c2:
    if COL["heard_hpv"] in df.columns:
        pct = round(df[df[COL["heard_hpv"]] == "نعم"].shape[0] / n * 100, 1)
        st.metric("💡 Connaissent HPV", f"{pct}%")
with c3:
    if COL["vaccine_exists"] in df.columns:
        pct2 = round(df[df[COL["vaccine_exists"]] == "نعم"].shape[0] / n * 100, 1)
        st.metric("💉 Savent qu'un vaccin existe", f"{pct2}%")
with c4:
    if COL["hpv_cancer"] in df.columns:
        pct3 = round(df[df[COL["hpv_cancer"]] == "نعم"].shape[0] / n * 100, 1)
        st.metric("🎗️ HPV = cause cancer col", f"{pct3}%")

st.markdown("---")

# ── Graphique 1 & 2 — Démographie ────────────
st.markdown('<div class="block-title">👤 Qui a répondu ?</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    if COL["genre"] in df.columns:
        s = df[COL["genre"]].value_counts()
        fig = px.pie(values=s.values, names=s.index, title="Genre — الجنس",
                     color_discrete_sequence=COLOR_SEQ, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=320, showlegend=False, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if COL["age"] in df.columns:
        age_order = ["أقل من 18 عامًا","18–25 عامًا","26–40 عامًا","41–60 عامًا","أكثر من 60 عامًا"]
        s = df[COL["age"]].value_counts().reindex([a for a in age_order if a in df[COL["age"]].unique()])
        fig = px.bar(x=s.index, y=s.values, title="Tranche d'âge — الفئة العمرية",
                     color=s.index, color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(height=320, showlegend=False, xaxis_tickangle=-20,
                          margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Graphique 3 & 4 — Connaissance + Confiance ─
st.markdown('<div class="block-title">📚 Connaissance & Confiance</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    # Niveau de connaissance HPV (3 questions combinées en barres)
    knowledge = {}
    if COL["heard_hpv"] in df.columns:
        knowledge["Ont entendu parler de HPV"] = round(df[df[COL["heard_hpv"]] == "نعم"].shape[0] / n * 100, 1)
    if COL["hpv_cancer"] in df.columns:
        knowledge["Savent HPV → cancer col"] = round(df[df[COL["hpv_cancer"]] == "نعم"].shape[0] / n * 100, 1)
    if COL["vaccine_exists"] in df.columns:
        knowledge["Savent qu'un vaccin existe"] = round(df[df[COL["vaccine_exists"]] == "نعم"].shape[0] / n * 100, 1)
    if knowledge:
        k_df = pd.DataFrame({"Question": list(knowledge.keys()), "% Oui": list(knowledge.values())})
        fig = px.bar(k_df, x="% Oui", y="Question", orientation="h",
                     title="Niveau de connaissance (%)",
                     color="Question", color_discrete_sequence=COLOR_SEQ,
                     text="% Oui")
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(height=320, showlegend=False, xaxis_range=[0,110],
                          margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if COL["state_trust"] in df.columns:
        trust_order = ["ثقة تامة","ثقة نسبية","لست متأكدًا","ثقة ضعيفة","لا ثقة على الإطلاق"]
        trust_fr    = ["Confiance totale","Confiance relative","Pas sûr(e)","Faible confiance","Aucune confiance"]
        s = df[COL["state_trust"]].value_counts()
        s = s.reindex([t for t in trust_order if t in s.index])
        labels_fr = [trust_fr[trust_order.index(t)] for t in s.index]
        colors_t  = ["#00B894","#00CEC9","#FDCB6E","#E17055","#D63031"]
        fig = px.bar(x=labels_fr, y=s.values,
                     title="Confiance dans les vaccins de l'État",
                     color=labels_fr,
                     color_discrete_sequence=colors_t)
        fig.update_layout(height=320, showlegend=False,
                          margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Graphique 5 & 6 — Obstacles + Canal ──────
st.markdown('<div class="block-title">🚧 Obstacles & Communication</div>', unsafe_allow_html=True)
col1, col2 = st.columns(2)

with col1:
    if COL["barriers"] in df.columns:
        s = explode_multi(df, COL["barriers"]).head(7)
        fig = px.bar(x=s.values, y=s.index, orientation="h",
                     title="Principaux obstacles à l'acceptation du vaccin",
                     color=s.index, color_discrete_sequence=COLOR_SEQ)
        fig.update_layout(height=370, showlegend=False,
                          margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if COL["best_channel"] in df.columns:
        s = df[COL["best_channel"]].value_counts()
        fig = px.pie(values=s.values, names=s.index,
                     title="Canal le + efficace pour corriger les idées reçues",
                     color_discrete_sequence=COLOR_SEQ, hole=0.45)
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=370, showlegend=False,
                          margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Insights automatiques ─────────────────────
st.markdown("---")
st.markdown('<div class="block-title">💡 Points clés</div>', unsafe_allow_html=True)

insights = []
if COL["heard_hpv"] in df.columns:
    p = round(df[df[COL["heard_hpv"]] == "نعم"].shape[0] / n * 100)
    insights.append(f"🔵 <b>{p}%</b> des participants ont déjà entendu parler de HPV.")
if COL["vaccine_exists"] in df.columns:
    p = round(df[df[COL["vaccine_exists"]] == "نعم"].shape[0] / n * 100)
    insights.append(f"💉 <b>{p}%</b> savent qu'un vaccin contre HPV existe.")
if COL["state_trust"] in df.columns:
    no_t = round(df[df[COL["state_trust"]].isin(["ثقة ضعيفة","لا ثقة على الإطلاق"])].shape[0] / n * 100)
    insights.append(f"⚠️ <b>{no_t}%</b> ont une confiance faible ou nulle dans les vaccins de l'État.")
if COL["barriers"] in df.columns:
    top = explode_multi(df, COL["barriers"])
    if len(top): insights.append(f"🚧 Obstacle principal : <b>{top.index[0]}</b>")
if COL["best_channel"] in df.columns:
    top_ch = df[COL["best_channel"]].value_counts()
    if len(top_ch): insights.append(f"📢 Canal préféré : <b>{top_ch.index[0]}</b>")

c1, c2 = st.columns(2)
for i, ins in enumerate(insights):
    with (c1 if i % 2 == 0 else c2):
        st.markdown(f'<div class="insight">{ins}</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("<center><small>Dashboard HPV · Streamlit & Plotly</small></center>", unsafe_allow_html=True)