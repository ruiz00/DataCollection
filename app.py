import streamlit as st
import pandas as pd
import numpy as np 
import plotly.express as px
import sqlite3 , html , logging ,os , hashlib
from datetime import datetime, datetime


logging.basicConfig(level = logging.INFO,format = "%(asctimes)s %(levelname)s %(message)s")

logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="DataSante CAM"
    layout="wide"
    initial_sidebar_state="expanded")

DB_PATH = os.environ.get("DB_PATH","datasante.db") # db config via environment variable

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

USERS ={}

def check_login(username : str , password : str) -> bool:
    h = hashlib.sha256(password.encode()).hexdigest()
    return USERS.get(username)== h
if "authenticated" not in st.session_state:
    st.session_state.authenticated= False
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.markdown("""
    <div class="main-header">
        <h1>🏥 DataSanté CM</h1>
        <p>Connexion requise</p>
    </div>
    """, unsafe_allow_html=True)
    with st.form("login_form"):
        username= st.text_input("Identifiant")
        password=st.text_input("mot de passe ", type="password")
        if st.form_submit_button("Se Connecter", use_container_width=True):
            st.session_state.authenticated= True
            st.session_state.username = username
            logger.info("Connexion reussie : %s ", username)
            st.rerun()
        else:
            st.error("Identifiant ou mot de passe incorrect ")
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

def get_conn_to_DB():
    return sqlite3.connect(DB_PATH)

def init_db():
    try:
        with get_conn_to_DB()as conn:
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
                    poids REAL CHECK(poids BETWEEN 1 AND 250),
                    tension_systolique INTEGER,
                    tension_diastolique INTEGER,
                    hospitalise TEXT NOT NULL,
                    issue TEXT NOT NULL,
                    duree_sejour INTEGER DEFAULT 0,
                    observations TEXT,
                    saisie_par TEXT
                )
            """)
            conn.commit()
    except sqlite3.Error as e:
        logger.error("Erreur init de la base de donnees : %s ",e)
        st.error("Impossible d'initialiser la base de donnees")

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