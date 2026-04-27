# DataSanté CAM 

Application de collecte et d'analyse descriptive des données épidémiologiques
au Cameroun. Développée en Python avec Streamlit.

## Fonctionnalités
- Formulaire de saisie structuré (région, district, formation sanitaire, données cliniques)
- Stockage persistant SQLite
- Analyse descriptive complète (moyenne, médiane, écart-type, IQR, fréquences)
- Visualisations interactives (histogrammes, camemberts, box plots, heatmap de corrélation)
- Export CSV
- Recherche et filtrage des données

## Déploiement local
```bash
pip install -r requirements.txt
streamlit run app.py
```
 
gwanulagabryan-nyagha23v2244-datacollection

## Déploiement Streamlit Cloud
1. Pousser ce dossier sur GitHub (dépôt public ou privé)
2. Se connecter sur https://share.streamlit.io
3. Cliquer "New app" → sélectionner le dépôt et `app.py`
4. Cliquer "Deploy" — l'URL publique est générée automatiquement

## Structure
```
datasante/
├── app.py           # Application principale
├── requirements.txt # Dépendances Python
└── README.md
```

## Auteur
GWANULAGA BRYAN NYAGHA L2 INOFRMATIQUE Université de Yaoundé I
