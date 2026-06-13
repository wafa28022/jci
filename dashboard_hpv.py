"""
Dashboard HPV — Analyse Professionnelle (version corrigée)
Lancer : streamlit run dashboard_hpv.py
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

st.set_page_config(
    page_title="Analyse HPV — Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

C       = ["#6C5CE7","#00CEC9","#FD79A8","#FDCB6E","#00B894","#E17055","#74B9FF","#A29BFE"]
GREEN   = "#00B894"
ORANGE  = "#E17055"
PURPLE  = "#6C5CE7"
YELLOW  = "#FDCB6E"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stMetric"] {
    background: linear-gradient(135deg,#f4f1ff,#eaf9f7);
    border-radius: 16px; padding: 20px;
    border-left: 5px solid #6C5CE7;
    box-shadow: 0 2px 8px rgba(108,92,231,0.10);
}
[data-testid="stMetricValue"] { font-size: 2rem !important; font-weight: 700; color: #6C5CE7; }
.section-header {
    font-size: 1.2rem; font-weight: 700; color: #2D3436;
    background: linear-gradient(90deg,#f4f1ff 0%,#fff 100%);
    border-left: 5px solid #6C5CE7; border-radius: 0 10px 10px 0;
    padding: 10px 18px; margin: 2rem 0 1rem 0;
    box-shadow: 0 2px 6px rgba(108,92,231,0.08);
}
.insight-card {
    background: #fff; border-radius: 14px; padding: 16px 20px; margin: 8px 0;
    border-left: 5px solid #6C5CE7;
    box-shadow: 0 2px 10px rgba(0,0,0,0.07);
    font-size: 0.97rem; line-height: 1.6;
}
.insight-card.orange { border-left-color: #E17055; }
.insight-card.green  { border-left-color: #00B894; }
.insight-card.pink   { border-left-color: #FD79A8; }
.hero {
    background: linear-gradient(135deg,#6C5CE7 0%,#00CEC9 100%);
    border-radius: 18px; padding: 32px 36px; margin-bottom: 2rem; color: white;
}
.hero h1 { font-size: 2rem; font-weight: 700; margin: 0; }
.hero p  { font-size: 1rem; opacity: 0.88; margin: 8px 0 0 0; }
</style>
""", unsafe_allow_html=True)

# ── Colonnes exactes du fichier ───────────────
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

# ── Helpers ───────────────────────────────────
def safe_str(series):
    """Convertit toujours en string pour éviter AttributeError."""
    return series.fillna("").astype(str)

def explode_multi(df, col):
    if col not in df.columns: return pd.Series(dtype=str)
    s = safe_str(df[col]).str.split(",").explode().str.strip()
    return s[s != ""].value_counts()

def trust_to_num(val):
    """Convertit les valeurs de confiance mixtes (str/int) en nombre 1-5."""
    if pd.isna(val): return None
    v = str(val).strip()
    if v.startswith("1") or "لا أثق" in v: return 1
    if v.startswith("5") or "ثقة تامة" in v: return 5
    try: return int(float(v))
    except: return None

def literacy_score(row):
    """Score 0-5 de connaissance réelle sur HPV."""
    score = 0
    if str(row.get(COL["heard_hpv"],"")).strip() == "نعم": score += 1
    if str(row.get(COL["hpv_what"],"")).strip() == "فيروس يمكن أن يؤدي إلى السرطان": score += 1
    if str(row.get(COL["hpv_cancer"],"")).strip() == "نعم": score += 1
    if "الاتصال الجنسي" in str(row.get(COL["transmission"],"")): score += 1
    if str(row.get(COL["vaccine_exists"],"")).strip() == "نعم": score += 1
    return score

def pct_contains(df, col, val):
    """% de lignes contenant val dans la colonne col."""
    if col not in df.columns: return 0
    return round(safe_str(df[col]).str.contains(val, na=False).sum() / len(df) * 100, 1)

def pct_equals(df, col, val):
    """% de lignes égales à val dans la colonne col."""
    if col not in df.columns: return 0
    return round((safe_str(df[col]).str.strip() == val).sum() / len(df) * 100, 1)

# ── Sidebar ───────────────────────────────────
with st.sidebar:
    st.markdown("## Source de données")
    source = st.radio("", ["Google Sheets (public)", "Fichier Excel/CSV"])
    df_raw = None

    if source == "Google Sheets (public)":
        st.info("Fichier → Partager → Tout le monde → Lecteur")
        url = st.text_input("URL Google Sheets", placeholder="https://docs.google.com/spreadsheets/d/...")
        if url:
            with st.spinner("Chargement..."):
                try:
                    sid = url.split("spreadsheets/d/")[1].split("/")[0]
                    df_raw = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sid}/export?format=csv")
                    st.success(f"✅ {len(df_raw)} réponses")
                except Exception as e:
                    st.error(f"Erreur : {e}")
    else:
        up = st.file_uploader("Déposer un fichier", type=["xlsx","xls","csv"])
        if up:
            try:
                df_raw = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up, engine="openpyxl")
                st.success(f"✅ {len(df_raw)} réponses")
            except Exception as e:
                st.error(f"Erreur : {e}")

    df = df_raw.copy() if df_raw is not None else None

    if df is not None:
        st.markdown("---")
        st.markdown("### Filtres")
        opts_g = ["Tous"] + sorted(df[COL["genre"]].dropna().unique().tolist())     if COL["genre"]     in df.columns else ["Tous"]
        opts_a = ["Tous"] + sorted(df[COL["age"]].dropna().unique().tolist())       if COL["age"]       in df.columns else ["Tous"]
        opts_e = ["Tous"] + sorted(df[COL["education"]].dropna().unique().tolist()) if COL["education"] in df.columns else ["Tous"]
        fg = st.selectbox("Genre",     opts_g)
        fa = st.selectbox("Age",       opts_a)
        fe = st.selectbox("Education", opts_e)
        if fg != "Tous": df = df[safe_str(df[COL["genre"]])     == fg]
        if fa != "Tous": df = df[safe_str(df[COL["age"]])       == fa]
        if fe != "Tous": df = df[safe_str(df[COL["education"]]) == fe]
        st.markdown(f"**Reponses filtrees :** `{len(df)}`")

# ── MAIN ─────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>Analyse — Sondage HPV</h1>
  <p>استبيان مجهول حول فيروس الورم الحليمي البشري ولقاحه · Tableau de bord analytique professionnel</p>
</div>
""", unsafe_allow_html=True)

if df is None:
    st.info("Connecte ta source de donnees dans la barre laterale pour commencer.")
    st.stop()

n = len(df)

# Calculer le score de litteratie (garde pour analyse 3 et 4)
df = df.copy()
df["_literacy"] = df.apply(literacy_score, axis=1)

# ── KPIs ──────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("Participants", n)
with k2: st.metric("Connaissent HPV", f"{pct_equals(df, COL['heard_hpv'], 'نعم')}%")
with k3: st.metric("Savent qu'un vaccin existe", f"{pct_equals(df, COL['vaccine_exists'], 'نعم')}%")
with k4:
    if COL["state_trust"] in df.columns:
        p = round(safe_str(df[COL["state_trust"]]).isin(["ثقة تامة","ثقة نسبية"]).sum() / n * 100, 1)
        st.metric("Confiance dans l'Etat", f"{p}%")

st.markdown("---")

# ══════════════════════════════════════════════
#  ANALYSE 1 — Profil Hesitant vs Acceptant
# ══════════════════════════════════════════════
st.markdown('<div class="section-header">Analyse 1 — Profil Hesitant vs Acceptant</div>', unsafe_allow_html=True)
st.caption("Qui accepte le vaccin et qui hesite ? Comparaison des profils selon le niveau de connaissance et les obstacles declares.")

if COL["reconsider"] in df.columns:
    df["_groupe"] = safe_str(df[COL["reconsider"]]).apply(
        lambda x: "Acceptant" if x.strip() == "نعم" else ("Hesitant/Refus" if x.strip() in ["لا","ربما","لست متأكدًا"] else None)
    )
    grp = df[df["_groupe"].notna()].copy()

    if len(grp) > 0:
        col1, col2 = st.columns(2)

        with col1:
            lit_grp = grp.groupby("_groupe")["_literacy"].mean().reset_index()
            lit_grp.columns = ["Groupe","Score moyen"]
            fig = px.bar(lit_grp, x="Groupe", y="Score moyen",
                         title="Score de litteratie moyen par groupe",
                         color="Groupe",
                         color_discrete_map={"Acceptant":GREEN,"Hesitant/Refus":ORANGE},
                         text="Score moyen")
            fig.update_traces(texttemplate="%{text:.2f}/5", textposition="outside")
            fig.update_layout(height=350, showlegend=False,
                              margin=dict(t=50,b=20,l=10,r=10), yaxis_range=[0,5.5],
                              plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            if COL["education"] in df.columns:
                edu_grp = grp.groupby(["_groupe", COL["education"]]).size().reset_index(name="n")
                fig2 = px.bar(edu_grp, x=COL["education"], y="n", color="_groupe",
                              barmode="group",
                              title="Education : Acceptants vs Hesitants",
                              color_discrete_map={"Acceptant":GREEN,"Hesitant/Refus":ORANGE})
                fig2.update_layout(height=350, xaxis_tickangle=-20, legend_title="Groupe",
                                   margin=dict(t=50,b=20,l=10,r=10),
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)

        if COL["barriers"] in df.columns:
            hesitants = grp[grp["_groupe"] == "Hesitant/Refus"]
            if len(hesitants) > 0:
                barr = explode_multi(hesitants, COL["barriers"]).head(6)
                fig3 = px.bar(x=barr.values, y=barr.index, orientation="h",
                              title="Obstacles principaux chez les Hesitants uniquement",
                              color=barr.index, color_discrete_sequence=C, text=barr.values)
                fig3.update_traces(textposition="outside")
                fig3.update_layout(height=380, showlegend=False,
                                   margin=dict(t=50,b=20,l=10,r=10),
                                   plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig3, use_container_width=True)

        acc_pct = round(grp[grp["_groupe"]=="Acceptant"].shape[0]/len(grp)*100)
        st.markdown(f'<div class="insight-card green">{acc_pct}% des repondants sont prets a reconsiderer leur position sur avis medical. Les hesitants se distinguent par un score de litteratie plus faible et des obstacles lies a la mefiance et au manque d\'information.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  ANALYSE 2 — Paradoxe Confiance-Connaissance
# ══════════════════════════════════════════════
st.markdown('<div class="section-header">Analyse 2 — Paradoxe Confiance-Connaissance</div>', unsafe_allow_html=True)
st.caption("Les personnes les mieux informees font-elles davantage confiance aux vaccins ? L'analyse revele parfois des resultats contre-intuitifs.")

if COL["state_trust"] in df.columns:
    trust_map = {"ثقة تامة":5,"ثقة نسبية":4,"لست متأكدًا":3,"ثقة ضعيفة":2,"لا ثقة على الإطلاق":1}
    df["_trust_num"] = safe_str(df[COL["state_trust"]]).str.strip().map(trust_map)

    col1, col2 = st.columns(2)

    with col1:
        lit_trust = df.groupby("_literacy")["_trust_num"].mean().reset_index()
        lit_trust.columns = ["Score Litteratie","Confiance moyenne"]
        lit_trust = lit_trust.dropna()
        fig = px.bar(lit_trust, x="Score Litteratie", y="Confiance moyenne",
                     title="Confiance moyenne selon le score de connaissance",
                     color="Confiance moyenne",
                     color_continuous_scale=["#E17055","#FDCB6E","#00B894"],
                     text="Confiance moyenne")
        fig.update_traces(texttemplate="%{text:.2f}/5", textposition="outside")
        fig.update_layout(height=370, coloraxis_showscale=False,
                          margin=dict(t=50,b=20,l=10,r=10), yaxis_range=[0,5.5],
                          plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if COL["education"] in df.columns:
            heat = pd.crosstab(safe_str(df[COL["education"]]), safe_str(df[COL["state_trust"]]))
            heat_pct = heat.div(heat.sum(axis=1), axis=0).round(2) * 100
            fig2 = px.imshow(heat_pct,
                             title="Education x Confiance dans les vaccins (%)",
                             color_continuous_scale="RdYlGn",
                             text_auto=".0f", aspect="auto")
            fig2.update_layout(height=370, margin=dict(t=50,b=20,l=10,r=10))
            st.plotly_chart(fig2, use_container_width=True)

    corr_data = df[["_literacy","_trust_num"]].dropna()
    if len(corr_data) > 5:
        corr = round(float(corr_data.corr().iloc[0,1]), 3)
        direction = "positive" if corr > 0 else "negative"
        force = "forte" if abs(corr) > 0.4 else ("moderee" if abs(corr) > 0.2 else "faible")
        msg = "Les mieux informes font davantage confiance aux vaccins." if corr > 0.1 else "Paradoxe : une meilleure connaissance ne se traduit pas forcement par plus de confiance — la mefiance est structurelle."
        st.markdown(f'<div class="insight-card pink">Correlation connaissance/confiance : r = {corr} ({direction}, {force}). {msg}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  ANALYSE 3 — Cartographie des Rumeurs
# ══════════════════════════════════════════════
st.markdown('<div class="section-header">Analyse 3 — Cartographie des Rumeurs par Niveau d\'Education</div>', unsafe_allow_html=True)
st.caption("Quelles fausses croyances circulent dans quels groupes ? Identifier les cibles prioritaires pour les campagnes de sensibilisation.")

if COL["myths"] in df.columns and COL["education"] in df.columns:
    myth_short = {
        "اللقاح يسبب العقم":                        "Vaccin cause sterilite",
        "اللقاح خطر على الصحة":                      "Vaccin dangereux",
        "اللقاح غير مختبر بشكل كافٍ":               "Pas assez teste",
        "الفتيات صغيرات جدًا على اللقاح":           "Filles trop jeunes",
        "اللقاح يشجع على العلاقات الجنسية المبكرة": "Encourage sexualite precoce",
        "المناعة الطبيعية أفضل من اللقاح":          "Immunite naturelle meilleure",
    }
    rows = []
    for edu, grp_edu in df.groupby(COL["education"]):
        myth_counts = explode_multi(grp_edu, COL["myths"])
        total = len(grp_edu)
        for myth, cnt in myth_counts.items():
            if "لم أسمع" not in myth:
                short = myth_short.get(myth.strip(), myth[:30])
                rows.append({"Niveau d'education": edu, "Rumeur": short, "pct": round(cnt/total*100,1)})

    if rows:
        df_myths = pd.DataFrame(rows)
        pivot = df_myths.pivot_table(index="Rumeur", columns="Niveau d'education", values="pct", aggfunc="mean").fillna(0)
        fig = px.imshow(pivot,
                        title="% exposes a chaque rumeur par niveau d'education",
                        color_continuous_scale="OrRd",
                        text_auto=".0f", aspect="auto",
                        labels=dict(color="% exposes"))
        fig.update_layout(height=420, margin=dict(t=50,b=20,l=10,r=10))
        st.plotly_chart(fig, use_container_width=True)

        top_myth = explode_multi(df[~safe_str(df[COL["myths"]]).str.contains("لم أسمع")], COL["myths"])
        if len(top_myth):
            top_name = myth_short.get(top_myth.index[0].strip(), top_myth.index[0])
            pct_myth = round(top_myth.iloc[0]/n*100)
            st.markdown(f'<div class="insight-card orange">La rumeur la plus repandue est "{top_name}" — touchant {pct_myth}% des participants. La heatmap revele les segments les plus vulnerables a chaque type de desinformation.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
#  ANALYSE 4 — Radar Confiance des Sources
# ══════════════════════════════════════════════
st.markdown('<div class="section-header">Analyse 4 — Hierarchie de Confiance dans les Sources</div>', unsafe_allow_html=True)
st.caption("Qui a le plus d'influence pour changer les comportements ? Le medecin, la famille, les reseaux sociaux ?")

trust_sources = {
    "Medecin/Infirmier":    COL["tr_doctor"],
    "Ecole/Universite":     COL["tr_school"],
    "Medias officiels":     COL["tr_media"],
    "Reseaux sociaux":      COL["tr_social"],
    "Famille/Amis":         COL["tr_family"],
    "Associations locales": COL["tr_ngo"],
}

scores_src = {}
for label, col in trust_sources.items():
    if col in df.columns:
        vals = df[col].apply(trust_to_num).dropna()
        if len(vals): scores_src[label] = round(vals.mean(), 2)

if scores_src:
    col1, col2 = st.columns([1, 1])

    with col1:
        cats = list(scores_src.keys())
        vals = list(scores_src.values())
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=vals + [vals[0]],
            theta=cats + [cats[0]],
            fill="toself",
            line=dict(color=PURPLE, width=2),
            fillcolor="rgba(108,92,231,0.18)",
            marker=dict(size=8, color=PURPLE),
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0,5],
                                       tickvals=[1,2,3,4,5])),
            title="Radar — Confiance moyenne par source (/5)",
            height=420, margin=dict(t=60,b=20,l=40,r=40),
            showlegend=False,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        src_df = pd.DataFrame({"Source":list(scores_src.keys()),"Score":list(scores_src.values())}).sort_values("Score")
        colors_src = [GREEN if s >= 4 else (YELLOW if s >= 3 else ORANGE) for s in src_df["Score"]]
        fig_bar = go.Figure(go.Bar(
            x=src_df["Score"], y=src_df["Source"], orientation="h",
            marker_color=colors_src,
            text=[f"{v}/5" for v in src_df["Score"]],
            textposition="outside",
        ))
        fig_bar.update_layout(
            title="Score de confiance par source (trie)",
            height=420, xaxis_range=[0,5.8],
            margin=dict(t=50,b=20,l=10,r=60),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    top_src = max(scores_src, key=scores_src.get)
    low_src = min(scores_src, key=scores_src.get)
    gap     = round(scores_src[top_src] - scores_src[low_src], 2)
    st.markdown(f'<div class="insight-card green">{top_src} est la source la plus fiable ({scores_src[top_src]}/5), devant {low_src} ({scores_src[low_src]}/5). L\'ecart de {gap} points souligne l\'importance de mobiliser les professionnels de sante dans les campagnes HPV.</div>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────
st.markdown("---")
st.markdown("<center><small>Dashboard analytique HPV · Streamlit & Plotly · Donnees issues d'un sondage anonyme</small></center>", unsafe_allow_html=True)