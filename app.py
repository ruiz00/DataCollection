import streamlit as st
import pandas as pd
import numpy as np 
import plotly.express as px
import sqlite3 , html , logging ,os , hashlib
from datetime import datetime, date


logging.basicConfig(level = logging.INFO,format = "%(asctimes)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="DataSante CAM",
    layout="wide",
    initial_sidebar_state="expanded"
)
DB_PATH = os.environ.get("DB_PATH","datasante.db") # db config via environment variable
def get_conn_to_DB():
    return sqlite3.connect(DB_PATH)

def init_db():
    try:
        with get_conn_to_DB() as conn:
            # Table des patients existante
            conn.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_saisie TEXT NOT NULL,
                    region TEXT NOT NULL,
                    district TEXT NOT NULL,
                    formation_sanitaire TEXT NOT NULL,
                    age INTEGER NOT NULL CHECK(age BETWEEN 0 AND 120),
                    sexe TEXT NOT NULL,
                    maladie TEXT NOT NULL,
                    symptomes TEXT,
                    temperature REAL CHECK(temperature BETWEEN 34 AND 43),
                    poids REAL CHECK(poids BETWEEN 1 AND 500),
                    tension_systolique INTEGER,
                    tension_diastolique INTEGER,
                    hospitalise TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    duree_sejour INTEGER DEFAULT 0,
                    observations TEXT,
                    saisie_par TEXT
                )
            """)
            # NOUVELLE Table pour les utilisateurs
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logger.error("Erreur init de la base de donnees : %s ", e)
        st.error("Impossible d'initialiser la base de donnees")

# Initialiser la DB tout de suite pour que la table 'users' existe avant le login
init_db()
st.markdown("""
<style>
        .main-header {
        background: linear-gradient(135deg, #0F6E56 0%, #1D9E75 100%);
        padding: 2rem; border-radius: 12px; margin-bottom: 2rem; color: white;
        }
    .main-header h1 { color: white; margin: 0; font-size: 2rem; }
    .main-header p  { color: rgba(255,255,255,0.85); margin: 0.5rem 0 0; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; font-weight: 500; }
</style>
""", unsafe_allow_html=True
)# basic  css style 

def add_user(username: str, password: str) -> bool:
    """Ajoute un nouvel utilisateur avec un mot de passe hache."""
    h = hashlib.sha256(password.encode()).hexdigest()
    try:
        with get_conn_to_DB() as conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, h))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # L'utilisateur existe déjà (username est PRIMARY KEY)
        return False

def check_login(username: str, password: str) -> bool:
    """Vérifie si l'identifiant et le mot de passe correspondent dans la DB."""
    h = hashlib.sha256(password.encode()).hexdigest()
    try:
        with get_conn_to_DB() as conn:
            cur = conn.execute("SELECT 1 FROM users WHERE username=? AND password_hash=?", (username, h))
            return cur.fetchone() is not None
    except sqlite3.Error as e:
        logger.error("Erreur check_login : %s ", e)
        return False
    

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.markdown("""
    <div class="main-header">
        <h1>DataSanté CAM</h1>
        <p>Connexion ou Inscription requise</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Création des onglets pour séparer Login et Signup
    tab_login, tab_signup = st.tabs(["Se connecter", " S'inscrire"])
    
    # Onglet de connexion
    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Identifiant")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se Connecter", use_container_width=True):
                if check_login(username, password):
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    logger.info("Connexion reussie : %s", username)
                    st.rerun()
                else:
                    st.error("Identifiant ou mot de passe incorrect.")
                    
    # Onglet d'inscription
    with tab_signup:
        with st.form("signup_form"):
            new_username = st.text_input("Nouvel Identifiant")
            new_password = st.text_input("Nouveau mot de passe", type="password")
            confirm_password = st.text_input("Confirmer le mot de passe", type="password")
            
            if st.form_submit_button("Créer un compte", use_container_width=True):
                if not new_username or not new_password:
                    st.error("Veuillez remplir tous les champs.")
                elif new_password != confirm_password:
                    st.error("Les mots de passe ne correspondent pas.")
                elif len(new_password) < 6:
                    st.error("Le mot de passe doit contenir au moins 6 caractères.")
                else:
                    if add_user(new_username, new_password):
                        st.success("Compte créé avec succès ! Vous pouvez maintenant vous connecter via l'onglet 'Se connecter'.")
                    else:
                        st.error("Cet identifiant existe déjà. Veuillez en choisir un autre.")
    st.stop()
VALID_REGIONS ={
    "Adamaoua", "Centre", "Est", "Extreme-Nord", "Littoral",
    "Nord", "Nord-Ouest", "Ouest", "Sud", "Sud-Ouest"
}
VALID_MALADIES = {
    "Paludisme", "Cholera", "Fievre typhoide", "Tuberculose",
    "VIH/SIDA", "Diabete", "Hypertension", "Pneumonie",
    "Diarrhee aigue", "Meningite", "Rougeole", "Autre"
}
VALID_SEXES   = {"Masculin", "Feminin"}
VALID_ISSUES  = {"En traitement", "Gueri", "Decede", "Transfere", "Abandon"}
VALID_HOSPIT  = {"Oui", "Non"}

def validate_patient(data: dict) -> list[str]:
    errors = []
    if data["region"] not in VALID_REGIONS:
        errors.append("Region invalide.")
    if data["maladie"] not in VALID_MALADIES:
        errors.append("Maladie invalide.")
    if data["sexe"] not in VALID_SEXES:
        errors.append("Sexe invalide.")
    if data["issue"] not in VALID_ISSUES:
        errors.append("Issue clinique invalide.")
    if data["hospitalise"] not in VALID_HOSPIT:
        errors.append("Valeur hospitalisation invalide.")
    if not (0 <= data["age"] <= 120):
        errors.append("Âge hors bornes (0 - 120).")
    if not (34.0 <= data["temperature"] <= 42.5):
        errors.append("Température hors bornes (34 - 42.5 °C).")
    if not (1.0 <= data["poids"] <= 500.0):
        errors.append("Poids hors bornes (1 - 500 kg).")
    if not (60 <= data["tension_systolique"] <= 260):
        errors.append("Tension systolique hors bornes.")
    if not (40 <= data["tension_diastolique"] <= 160):
        errors.append("Tension diastolique hors bornes.")
    if not data["district"].strip():
        errors.append("Le district est obligatoire.")
    if not data["formation_sanitaire"].strip():
        errors.append("La formation sanitaire est obligatoire.")
    return errors

def insert_patient(data : dict) -> bool:
    try:
        with get_conn_to_DB() as conn:
            conn.execute(""" 
                         INSERT INTO patients(
                         date_saisie,region,district,formation_sanitaire,age
                         sexe,maladie,symptomes,temperature,poids,tension_systolique,tension_diastolique,
                         hospitalise,issue,duree_sejour,observations,saisie_par) VALUES ((?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                         
                         (data["date_saisie"], data["region"], data["district"],
                data["formation_sanitaire"], data["age"], data["sexe"],
                data["maladie"], data["symptomes"], data["temperature"],
                data["poids"], data["tension_systolique"], data["tension_diastolique"],
                data["hospitalise"], data["issue"], data["duree_sejour"],
                data["observations"], st.session_state.username
            ))
            conn.commit()
            logger.info("INSERT patient - maladie= %s region=%s par=%s", data["maladie"],data["region"],st.session_state.username)
            return True
    except sqlite3.Error as e :
        logger.error ("Erreur insertion d'un patient : %s",e)
        return False
    
@st.cache_data(ttl=30)
def load_data()->pd.DataFrame:
    try:
        with get_conn_to_DB() as conn:
            return pd.read_sql_query(
                "SELECT * FROM patients ORDER BY id DESC",conn)
    except sqlite3.Error as e:
        logger.error("Erreur load_data : %s ",e)
        return pd.DataFrame()
    
def delete_record(record_id: int )->bool:
    try:
        with get_conn_to_DB() as conn:
            cur = conn.execute(
                "SELECT id FROM patients WHERE id=?",(record_id))
            if cur.fetchone() is None:
                return False 
            conn.execute("DELETE FROM patients WHERE id=?",(record_id))
            conn.commit()
            logger.warning("DElETE patient id=%d par=%s", record_id, st.session_state.username)
            return True
    except sqlite3.Error as e:
        logger.error("Erreur delete_record id=%d: %s" , record_id,e)
        return False
    

def invalidate_cache():
    load_data.clear()

REGIONS   = sorted(VALID_REGIONS)
MALADIES  = sorted(VALID_MALADIES)
SYMPTOMES = [
    "Fièvre", "Toux", "Maux de tête", "Vomissements",
    "Diarrhée", "Douleurs abdominales", "Fatigue", "Dyspnée",
    "Frissons", "Perte d'appétit", "Éruption cutanée"
]
st.markdown("""
<div class="main-header">
    <h1>DataSante CAM</h1>
    <p>Système de Collecte et d'Analyse Descriptive des Donnees Epidemiologiques</p>
</div>
""", unsafe_allow_html=True)

init_db()

with st.sidebar:
    # FIX: image locale ou URL connue sûre — pas d'URL externe non maîtrisée
    st.markdown("### Navigation")
    df_sidebar = load_data()
    st.caption(f"Total fiches : **{len(df_sidebar)}**")
    st.markdown("---")
    st.markdown("TP INF232 ")
    st.caption("Secteur : Sante Publique · Cameroun")
    st.markdown("---")
    # FIX: bouton de déconnexion
    if st.button(" Se déconnecter"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.rerun()
    st.caption(f"Connecte : {st.session_state.username}")

# ─── Onglets 
tab1, tab2, tab3, tab4 = st.tabs([
    " Saisie des donnees",
    " Analyse descriptive",
    " Visualisations",
    " Données brutes"
])

# TAB 1 — Formulaire
with tab1:
    st.subheader("Fiche de collect epidemiologiaue")
    with st.form("form_patient",clear_on_submit=True):
        col1,col2 = st.columns(2)
        with col1:
            st.markdown("  Localisation *")
            region    = st.selectbox("Region *", REGIONS)
            district  = st.text_input("District de sante *",
                                      placeholder="Ex : Yaounde Centre",
                                      max_chars=100)
            formation = st.text_input("Formation sanitaire *",
                                      placeholder="Ex : CHUY, CS Mendong...",
                                      max_chars=150)
        with col2:
            st.markdown("**Patient**")
            age = st.number_input("Age (annees) *", min_value=0, max_value=120, value=30)
            sexe = st.radio("Sexe ", ["Masculin", "Féminin"],horizontal=True)
            date_saisie = st.date_input("Date de saisie *", value=date.today())
        st.markdown("---")
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("Donnees cliniques")
            maladie       = st.selectbox("Maladie / Pathologie *", MALADIES)
            symptomes_sel = st.multiselect("Symptomes observes *", SYMPTOMES)
            temperature   = st.number_input("Temperature (°C) *",min_value=34.0, max_value=42.5,value=37.0, step=0.1)
            poids         = st.number_input("Poids (kg) *",  min_value=1.0,max_value=500.0,value=65.0, step=0.1)
        with col4:
            st.markdown("Tension arterielle & Issue")
            ta_sys  = st.number_input("TA Systolique (mmHg) *",min_value=60, max_value=260, value=120)
            ta_dia  = st.number_input("TA Diastolique (mmHg) *",min_value=40, max_value=160, value=80)
            hospitalise = st.radio("Hospitalise ?", ["Oui", "Non"],horizontal=True)
            issue = st.selectbox("Issue clinique *",list(VALID_ISSUES))
            duree = st.number_input("Duree de sejour (jours) *",min_value=0, max_value=365, value=0)

        observations = st.text_area("Observations", height=80, max_chars=500)
        submitted = st.form_submit_button("Enregistrer la fiche",use_container_width=True,type="primary")
        if submitted:
            record = {
                "date_saisie": str(date_saisie),
                "region": region,
                "district": district.strip(),
                "formation_sanitaire": formation.strip(),
                "age": age, "sexe": sexe, "maladie": maladie,
                "symptomes": ", ".join(symptomes_sel),
                "temperature": round(temperature, 1),
                "poids": round(poids, 1),
                "tension_systolique": ta_sys,
                "tension_diastolique": ta_dia,
                "hospitalise": hospitalise, "issue": issue,
                "duree_sejour": duree,
                "observations": observations.strip()
            }
            # FIX: validation côté serveur avant toute insertion
            errors = validate_patient(record)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                if insert_patient(record):
                    invalidate_cache()
                    st.success(f"Fiche enregistree — {maladie} | {region} | {date_saisie}")
                    st.rerun()
                else:
                    st.error("Erreur lors de l'enregistrement. Veuillez reessayer.")


### TAB 2 Analyse descriptive
with tab2:
    df= load_data()
    if df.empty:
        st.info("Aucune donnee disponible")
    else:
        st.subheader("Statistiques generales")
        m1,m2,m3, m4, m5 = st.columns(5)
        m1.metric("Total fiches" , len(df))
        m2.metric("Age moyen", f"{df['age'].mean():.1f} ans")
        m3.metric("Temp. moy.", f"{df['temperature'].mean():.1f} °C")
        m4.metric("Hospitalises", (df["hospitalise"] == "Oui").sum())
        m5.metric("Deces", (df["issue"] == "Décédé").sum())
        st.markdown("---")
        with st.expander("Filtrer"):
            fc1, fc2, fc3 = st.columns(3)
            f_region  = fc1.multiselect("Région",  df["region"].unique())
            f_maladie = fc2.multiselect("Maladie", df["maladie"].unique())
            f_sexe    = fc3.multiselect("Sexe",    df["sexe"].unique())

        df_f = df.copy()
        if f_region:  df_f = df_f[df_f["region"].isin(f_region)]
        if f_maladie: df_f = df_f[df_f["maladie"].isin(f_maladie)]
        if f_sexe:    df_f = df_f[df_f["sexe"].isin(f_sexe)]

        st.markdown(f"**{len(df_f)} enregistrement(s) selectionne(s)**")

        num_cols = ["age", "temperature", "poids", "tension_systolique",
                    "tension_diastolique", "duree_sejour"]
        labels = {
            "age": "Age (ans)", "temperature": "Temperature (°C)",
            "poids": "Poids (kg)", "tension_systolique": "TA Systolique",
            "tension_diastolique": "TA Diastolique",
            "duree_sejour": "Durée séjour (j)"
        }
        st.subheader("Variables quantitatives")
        rows=[]
        for col_name in num_cols:
            s = df_f[col_name].dropna()
            if len(s):
                q1, q3 = s.quantile(0.25), s.quantile(0.75)
                rows.append({
                    "Variable": labels[col_name], "N": len(s),
                    "Moyenne": round(s.mean(), 2),
                    "Mediane": round(s.median(), 2),
                    "Écart-type": round(s.std(), 2),
                    "Min": round(s.min(), 2), "Max": round(s.max(), 2),
                    "Q1": round(q1, 2), "Q3": round(q3, 2),
                    "IQR": round(q3 - q1, 2),
                })
        if rows:
            st.dataframe(pd.DataFrame(rows).set_index("Variable"), use_container_width=True)

            st.subheader("Variables Qualitatives - Frequences")
            for col_name,label in {"region": "Region", "maladie": "Maladie",
            "sexe": "Sexe", "issue": "Issue", "hospitalise": "Hospitalise"
            }.items():
                freq = df_f[col_name].value_counts().reset_index()
                freq.columns = [label, "Effectif"]
                freq["Fréquence (%)"] = (freq["Effectif"] / len(df_f) * 100).round(1)
                with st.expander(f"Distribution — {label}"):
                    st.dataframe(freq, use_container_width=True, hide_index=True)
        
        st.subheader("Matrice de correlation")
        corr_df = df_f[num_cols].dropna()
        if len(corr_df) >= 3:
            corr = corr_df.rename(columns=labels).corr().round(2)
            fig_c = px.imshow(corr, text_auto=True,
                              color_continuous_scale="RdYlGn",
                              title="Correlations entre variables numeriques",
                              zmin=-1, zmax=1)
            fig_c.update_layout(height=450)
            st.plotly_chart(fig_c, use_container_width=True)
        else:
            st.info("Minimum 3 lignes requises pour la matrice de correlation.")


### TAB  3 VISUALISATION DES DONNEES
with tab3:
    df = load_data()
    if df.empty:
        st.info("Aucun donnes a visualiser")
    else:
        PALETTE = px.colors.qualitative.Vivid
        c1, c2 = st.columns(2)
        with c1:
            fig = px.histogram(df, x="age", nbins=15, color="sexe",title="Distribution des ages par sexe",labels={"age": "Age (ans)", "count": "Effectif"},
                               color_discrete_map={"Masculin": "#378ADD","Féminin": "#D4537E"},barmode="overlay", opacity=0.75)
            fig.update_layout(height=360, legend_title_text="Sexe")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fm = df["maladie"].value_counts().reset_index()
            fm.columns = ["maladie", "effectif"]
            fig2 = px.bar(fm, x="effectif", y="maladie", orientation="h",title="Frequence des maladies",color="effectif", color_continuous_scale="Tealgrn")
            fig2.update_layout(height=360, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns(2)
        with c3:
            fig3 = px.pie(df, names="issue",title="Repartition des issues cliniques",color_discrete_sequence=PALETTE, hole=0.4)
            fig3.update_layout(height=360)
            st.plotly_chart(fig3, use_container_width=True)
        with c4:
            fr = df["region"].value_counts().reset_index()
            fr.columns = ["region", "cas"]
            fig4 = px.bar(fr, x="region", y="cas", title="Cas par region",color="cas", color_continuous_scale="Greens")
            fig4.update_xaxes(tickangle=-35)
            fig4.update_layout(height=360, showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

        st.subheader("Box plots")
        var_bp = st.selectbox("Variable", ["age","temperature","poids","tension_systolique","duree_sejour"],
                              format_func=lambda x: {
                                  "age":"Age","temperature":"Temperature",
                                  "poids":"Poids","tension_systolique":"TA Systolique",
                                  "duree_sejour":"Duree de séjour"}[x])
        fig5 = px.box(df, x="maladie", y=var_bp, color="sexe",
                      color_discrete_map={"Masculin":"#378ADD","Féminin":"#D4537E"},
                      title=f"Distribution de {var_bp} par maladie",
                      points="all")
        fig5.update_xaxes(tickangle=-30)
        fig5.update_layout(height=420)
        st.plotly_chart(fig5, use_container_width=True)

        df2 = df.copy()
        df2["date_saisie"] = pd.to_datetime(df2["date_saisie"], errors="coerce")
        daily = df2.groupby("date_saisie").size().reset_index(name="cas")
        if len(daily) > 1:
            fig6 = px.line(daily, x="date_saisie", y="cas",
                           title="Évolution temporelle des cas",
                           markers=True, line_shape="spline",
                           color_discrete_sequence=["#1D9E75"])
            fig6.update_layout(height=320)
            st.plotly_chart(fig6, use_container_width=True)

# TAB 4 — Données brutes
with tab4:
    df = load_data()
    st.subheader(f"Base de donnees — {len(df)} enregistrement(s)")

    if not df.empty:
        search = st.text_input("Rechercher", max_chars=100)  # FIX: limite longueur
        if search:
            # FIX: regex=False pour éviter ReDoS
            safe_search = search.strip()
            mask = df.apply(
                lambda row: row.astype(str).str.contains(
                    safe_search, case=False, na=False, regex=False
                ).any(), axis=1)
            df_show = df[mask]
        else:
            df_show = df

        st.dataframe(df_show, use_container_width=True, height=400)

        col_dl, col_del = st.columns([3, 1])
        with col_dl:
            csv = df_show.to_csv(index=False).encode("utf-8")
            st.download_button(
                "Exporter en CSV", data=csv,
                file_name=f"datasante_export_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        with col_del:
            with st.popover("Supprimer une fiche"):
                del_id = st.number_input("ID de la fiche", min_value=1, step=1)
                if st.button("Confirmer la suppression", type="primary"):
                    # FIX: vérification d'existence + bool de retour
                    if delete_record(int(del_id)):
                        invalidate_cache()
                        st.success(f"Fiche {del_id} supprimée.")
                        st.rerun()
                    else:
                        st.error(f"Fiche {del_id} introuvable ou erreur DB.")
    else:
        st.info("Aucune donnee enregistree.")
