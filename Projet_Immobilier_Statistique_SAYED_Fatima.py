#!/usr/bin/env python
# coding: utf-8

# # Projet M2 — Économétrie appliquée
# ## Analyse des prix immobiliers (2015–2023)
# Notebook complet : descriptif, MCO, diagnostics, rupture COVID, Ridge/Lasso, export (figures, tables, DOCX/PDF).
# 
# **Entrée** : `donnees_immobilieres_extended.xlsx` (même dossier que le notebook).

# In[1]:


# =========================
# Imports & configuration
# =========================
import os, math, json, datetime, zipfile
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Disable GUI backend

from pathlib import Path
FIGURES_DIR = Path('figures')
FIGURES_DIR.mkdir(exist_ok=True)

import matplotlib.pyplot as plt

import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson
from statsmodels.stats.outliers_influence import variance_inflation_factor

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, LassoCV, Ridge, Lasso
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error

from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

plt.rcParams["figure.figsize"] = (8,5)
plt.rcParams["axes.grid"] = True


# In[2]:


# =========================
# Paramètres / chemins
# =========================
DATA_PATH = "donnees_immobilieres_extended.xlsx"  # adapte si besoin

FIG_DIR = "figures_m2"
os.makedirs(FIG_DIR, exist_ok=True)

DOCX_PATH = "Rapport_final_M2_Analyse_Prix_Immobiliers.docx"
PDF_PATH  = "Rapport_final_M2_Analyse_Prix_Immobiliers.pdf"
TABLES_XLSX = "tables_resultats.xlsx"
FIG_ZIP = "Figures_projet_M2.zip"
SUMMARY_JSON = "summary_numbers.json"
MEAN_CSV = "mean_price_by_year.csv"


# In[3]:


# =========================
# Chargement des données
# =========================
df = pd.read_excel(DATA_PATH).copy()

df["Ascenseur"] = df["Ascenseur"].astype(int)
df["COVID"] = (df["Annee_vente"] >= 2020).astype(int)

y = df["Prix_milliers_euros"]

base_vars = ["Surface_m2","Chambres","Annee_construction","Distance_centre_km","Etage","Ascenseur"]
ext_vars  = base_vars + ["Qualite_ecole","Revenu_median_quartier","Annee_vente"]

feature_cols = ext_vars.copy()
if "Distance_universite" in df.columns:
    feature_cols.append("Distance_universite")

df.head()


# ## 1. Statistiques Descriptives et Analyse Préliminair
# ### 1.1 Statistiques descriptive

# In[4]:


cont_vars = ["Surface_m2","Chambres","Annee_construction","Distance_centre_km","Etage",
             "Annee_vente","Qualite_ecole","Revenu_median_quartier"]
if "Distance_universite" in df.columns:
    cont_vars.append("Distance_universite")

desc = df[cont_vars + ["Prix_milliers_euros","Ascenseur"]].describe().T
desc = desc.rename(columns={"50%": "median"})
desc["skewness"] = df[cont_vars + ["Prix_milliers_euros","Ascenseur"]].skew(numeric_only=True)
desc["kurtosis"] = df[cont_vars + ["Prix_milliers_euros","Ascenseur"]].kurtosis(numeric_only=True)
desc


# Asymétrie et aplatissement du prix

# In[5]:


from scipy.stats import skew, kurtosis

# Asymétrie et aplatissement du prix (variable dépendante)
prix_skewness = skew(df["Prix_milliers_euros"], nan_policy="omit")
prix_kurtosis = kurtosis(df["Prix_milliers_euros"], nan_policy="omit")

print("Asymétrie (skewness) du prix :", round(prix_skewness, 3))
print("Aplatissement (kurtosis) du prix :", round(prix_kurtosis, 3))


# Histogrammes des principales variables quantitatives et Boîtes à moustaches (détection des valeurs extrêmes)

# In[11]:


def save_hist(series, title, fname, bins=20):
    plt.figure()
    plt.hist(series.dropna(), bins=20, edgecolor="black")
    plt.title(title)
    plt.xlabel(series.name)
    plt.ylabel("Fréquence")
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, fname), dpi=220)
    plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
    plt.close()
    plt.close()

def save_box(series, title, fname):
    plt.figure()
    plt.boxplot(series.dropna(), vert=True)
    plt.title(title)
    plt.ylabel(series.name)
    plt.tight_layout()
    plt.savefig(os.path.join(FIG_DIR, fname), dpi=220)
    plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
    plt.close()
    plt.close()

save_hist(df["Prix_milliers_euros"], "Histogramme du prix (k€)", "hist_prix.png")
save_box(df["Prix_milliers_euros"], "Boîte à moustaches du prix", "box_prix.png")
save_hist(df["Surface_m2"], "Histogramme de la surface (m²)", "hist_surface.png")
save_box(df["Surface_m2"], "Boîte à moustaches de la surface", "box_surface.png")
save_hist(df["Distance_centre_km"], "Histogramme de la distance au centre (km)", "hist_distance.png")


# ### 1.2 Analyse de corrélation
# 

# In[12]:


# =========================
# Matrice de corrélation (tableau)
# =========================
corr = df[cont_vars + ["Prix_milliers_euros"]].corr(numeric_only=True)

corr.round(3)


# Graphique de correlation

# In[13]:


corr = df[cont_vars + ["Prix_milliers_euros"]].corr(numeric_only=True)
plt.figure(figsize=(8,6))
plt.imshow(corr, aspect="auto")
plt.xticks(range(len(corr.columns)), corr.columns, rotation=90, fontsize=7)
plt.yticks(range(len(corr.index)), corr.index, fontsize=7)
plt.title("Heatmap de corrélation (variables continues)")
plt.colorbar()
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "heatmap_corr.png"), dpi=220)
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()
plt.close()


# In[14]:


# Paires les plus corrélées (en valeur absolue)
corr_abs = corr.abs()
np.fill_diagonal(corr_abs.values, 0)

corr_abs.unstack().sort_values(ascending=False).head(10)


# Identifier la variable la plus corrélée au prix

# In[15]:


corr["Prix_milliers_euros"].drop("Prix_milliers_euros").sort_values(
    key=abs, ascending=False
)


# In[16]:


# =========================
# Paires de variables fortement corrélées
# =========================

corr_abs = corr.abs()

# Supprimer la diagonale
np.fill_diagonal(corr_abs.values, 0)

# Seuil de forte corrélation (classique : 0.7)
seuil = 0.7

fortes_corr = (
    corr_abs
    .stack()
    .reset_index()
    .rename(columns={
        "level_0": "Variable 1",
        "level_1": "Variable 2",
        0: "Corrélation |ρ|"
    })
    .query("`Corrélation |ρ|` >= @seuil")
    .sort_values("Corrélation |ρ|", ascending=False)
)

fortes_corr


# ## 2) Modèles linéaires (MCO) + transformations log

# 2.1 Modèle de régression linéaire simple

# In[17]:


# Variable dépendante
y = df["Prix_milliers_euros"]

# Variable explicative + constante
X_simple = sm.add_constant(df[["Surface_m2"]])

# Estimation MCO
model_simple = sm.OLS(y, X_simple).fit()

# Résumé
model_simple.summary()


# * Extraction “propre” des éléments demandés

# In[18]:


results_simple = pd.DataFrame({
    "Coefficient": model_simple.params,
    "Ecart-type": model_simple.bse,
    "Statistique t": model_simple.tvalues,
    "p-valeur": model_simple.pvalues
})

results_simple


# * Qualité d’ajustement 

# In[19]:


print("R² :", round(model_simple.rsquared, 3))
print("R² ajusté :", round(model_simple.rsquared_adj, 3))


# * Estimation MCO

# In[20]:


import statsmodels.api as sm

# Variable dépendante
y = df["Prix_milliers_euros"]

# Variables explicatives
X_multi = df[
    ["Surface_m2", "Chambres", "Annee_construction",
     "Distance_centre_km", "Etage", "Ascenseur"]
]

# Ajout de la constante
X_multi = sm.add_constant(X_multi)

# Estimation MCO
model_multi = sm.OLS(y, X_multi).fit()

# Résumé des résultats
model_multi.summary()


# * Tableau clair des coefficients

# In[21]:


results_multi = pd.DataFrame({
    "Coefficient": model_multi.params,
    "Ecart-type": model_multi.bse,
    "Statistique t": model_multi.tvalues,
    "p-valeur": model_multi.pvalues
})

results_multi


# 2.2 Estimation du modèle de régression linéaire multiple

# In[22]:


model_multi_hc1 = model_multi.get_robustcov_results(cov_type="HC1")
model_multi_hc1.summary()


# 2.3 Transformations logarithmiques

# In[23]:


# Création de versions logarithmiques
df["log_prix"] = np.log(df["Prix_milliers_euros"])
df["log_surface"] = np.log(df["Surface_m2"])


# * Modèle semi-log (log-prix)

# In[24]:


y_log = df["log_prix"]

model_semilog = sm.OLS(y_log, X_multi).fit()
model_semilog.summary()

# Version robuste
model_semilog_hc1 = model_semilog.get_robustcov_results(cov_type="HC1")
model_semilog_hc1.summary()


# * Modèle log-log

# In[25]:


X_loglog = df[
    ["log_surface","Chambres","Annee_construction",
     "Distance_centre_km","Etage","Ascenseur",
     "Qualite_ecole","Revenu_median_quartier","Annee_vente"]
]

X_loglog = sm.add_constant(X_loglog)

model_loglog = sm.OLS(y_log, X_loglog).fit()
model_loglog.summary()

# Version robuste
model_loglog_hc1 = model_loglog.get_robustcov_results(cov_type="HC1")
model_loglog_hc1.summary()


# * Modèle log-log avec log_distance (ROBUSTESSE)

# In[26]:


# Création de la distance en log (évite log(0))
df["log_distance"] = np.log(df["Distance_centre_km"] + 1)

# Modèle log-log plus complet (robustesse)
X_loglog_robust = df[
    ["log_surface", "log_distance",
     "Chambres", "Annee_construction",
     "Etage", "Ascenseur"]
]

X_loglog_robust = sm.add_constant(X_loglog_robust)

model_loglog_robust = sm.OLS(df["log_prix"], X_loglog_robust).fit()
model_loglog_robust.summary()


# ## 3) Diagnostics : VIF, BP, DW, rupture COVID

# In[27]:


# Ajout de la constante
X_vif = sm.add_constant(df[ext_vars])
# Calcul des VIF
vif_df = pd.DataFrame({
    "variable": X_vif.columns,
    "VIF": [variance_inflation_factor(X_vif.values, i) for i in range(X_vif.shape[1])]
})
vif_df


# ## 4) Tests et inférence

# 4.1.Tester que la distance au centre a un effet négatif (test unilatéral)

# In[28]:


import scipy.stats as st
# suppose que ton modèle multiple en niveau est déjà estimé:
# model_multi = sm.OLS(y, X_multi).fit()

b = model_multi.params["Distance_centre_km"]
t = model_multi.tvalues["Distance_centre_km"]
df_resid = int(model_multi.df_resid)

# p-value unilatérale pour H1: beta < 0
p_one_sided = st.t.cdf(t, df=df_resid)  # si t est négatif, p sera petit

print("beta_distance =", b)
print("t-stat =", t)
print("p-value (unilatérale, H1: beta<0) =", p_one_sided)


# 4.2.1.Tester que tous les coefficients (sauf constante) sont nuls

# In[29]:


import numpy as np

# nombres de paramètres
k = len(model_multi.params)

# Matrice R : on teste toutes les pentes (on exclut la constante)
R = np.eye(k)[1:]   # enlève la constante (première ligne)
q = np.zeros(k-1)

ftest_global = model_multi.f_test((R, q))
print(ftest_global)


# 4.2.2. Tester si ajouter Qualite_ecole et Revenu_median_quartier améliore le modèle

# In[30]:


# Modèle restreint (déjà model_multi)
model_restricted = model_multi

# Modèle étendu
X_extended = df[
    ["Surface_m2","Chambres","Annee_construction",
     "Distance_centre_km","Etage","Ascenseur",
     "Qualite_ecole","Revenu_median_quartier"]
]
X_extended = sm.add_constant(X_extended)
model_extended = sm.OLS(df["Prix_milliers_euros"], X_extended).fit()

# Test F de comparaison (modèles emboîtés)
F_stat, p_val, df_diff = model_extended.compare_f_test(model_restricted)

print("F =", F_stat)
print("p-value =", p_val)
print("df diff =", df_diff)


# 4.3. Stabilité structurelle : effet COVID (rupture structurelle)

# * Méthode 1 (simple et claire) : Dummy COVID + interactions (test conjoint)

# In[31]:


# Définir la période COVID (ex: 2020-2023)
df["covid"] = (df["Annee_vente"] >= 2020).astype(int)

base_vars = ["Surface_m2","Chambres","Annee_construction","Distance_centre_km","Etage","Ascenseur",
             "Qualite_ecole","Revenu_median_quartier"]

# Matrice X de base
X_base = df[base_vars].copy()

# Ajout des interactions avec covid
for v in base_vars:
    X_base[f"covid_x_{v}"] = df["covid"] * df[v]

# Ajout du dummy covid (déplacement du niveau)
X_base["covid"] = df["covid"]

X_covid = sm.add_constant(X_base)
model_covid = sm.OLS(df["Prix_milliers_euros"], X_covid).fit()

model_covid.summary()


# * Test de rupture : test conjoint des interactions (et éventuellement du dummy)

# In[32]:


# Noms des paramètres du modèle
param_names = model_covid.params.index.tolist()

# Indices des coefficients d'interaction
interaction_idx = [
    param_names.index(f"covid_x_{v}") for v in base_vars
]

# Matrice R (une ligne par restriction)
R = np.zeros((len(interaction_idx), len(param_names)))
for i, idx in enumerate(interaction_idx):
    R[i, idx] = 1

# Vecteur q (tout à zéro)
q = np.zeros(len(interaction_idx))

# Test F conjoint : toutes les interactions = 0
ftest_int = model_covid.f_test((R, q))
print(ftest_int)


# * Méthode 2 : Chow test (comparaison SSR pré/post)

# In[33]:


def chow_test(df, year_break=2020, y_col="Prix_milliers_euros", x_cols=None):
    if x_cols is None:
        raise ValueError("x_cols doit être fourni")

    df_pre = df[df["Annee_vente"] < year_break]
    df_post = df[df["Annee_vente"] >= year_break]

    X_pre = sm.add_constant(df_pre[x_cols])
    y_pre = df_pre[y_col]
    m_pre = sm.OLS(y_pre, X_pre).fit()

    X_post = sm.add_constant(df_post[x_cols])
    y_post = df_post[y_col]
    m_post = sm.OLS(y_post, X_post).fit()

    X_full = sm.add_constant(df[x_cols])
    y_full = df[y_col]
    m_full = sm.OLS(y_full, X_full).fit()

    SSR_pooled = np.sum(m_full.resid**2)
    SSR_pre = np.sum(m_pre.resid**2)
    SSR_post = np.sum(m_post.resid**2)

    k = X_full.shape[1]  # nb paramètres (const incluse)
    n_pre = df_pre.shape[0]
    n_post = df_post.shape[0]

    F = ((SSR_pooled - (SSR_pre + SSR_post)) / k) / ((SSR_pre + SSR_post) / (n_pre + n_post - 2*k))
    p = 1 - st.f.cdf(F, dfn=k, dfd=(n_pre + n_post - 2*k))
    return F, p, (n_pre, n_post, k)

x_cols = ["Surface_m2","Chambres","Annee_construction","Distance_centre_km","Etage","Ascenseur",
          "Qualite_ecole","Revenu_median_quartier"]

F_chow, p_chow, info = chow_test(df, year_break=2020, x_cols=x_cols)
print("Chow test F =", F_chow)
print("p-value =", p_chow)
print("(n_pre, n_post, k) =", info)


# ## 5) Hétéroscédasticité et autocorrélation
# 

# 1. Résidus vs valeurs ajustées

# In[34]:


# Résidus et valeurs ajustées
residuals = model_multi.resid
fitted = model_multi.fittedvalues

plt.figure(figsize=(6,4))
plt.scatter(fitted, residuals, alpha=0.7)
plt.axhline(0, color="red", linestyle="--")
plt.xlabel("Valeurs ajustées")
plt.ylabel("Résidus")
plt.title("Résidus vs valeurs ajustées")
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()


# 1.2. Résidus dans le temps (année de vente)

# In[35]:


plt.figure(figsize=(6,4))
plt.scatter(df["Annee_vente"], residuals, alpha=0.7)
plt.axhline(0, color="red", linestyle="--")
plt.xlabel("Année de vente")
plt.ylabel("Résidus")
plt.title("Résidus et temps")
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()


# 1.2.3. QQ-plot des résidus standardisés (MCO)

# In[36]:


import statsmodels.api as sm
import matplotlib.pyplot as plt
import numpy as np

# Résidus standardisés
resid_std = model_multi.resid / np.std(model_multi.resid)

sm.qqplot(resid_std, line='45')
plt.title("QQ-plot des résidus standardisés (MCO)")
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()


# 2. Test formel d’hétéroscédasticité (Test de Breusch–Pagan)

# In[37]:


from statsmodels.stats.diagnostic import het_breuschpagan

bp_test = het_breuschpagan(residuals, model_multi.model.exog)

labels = ["LM stat", "LM p-value", "F stat", "F p-value"]
dict(zip(labels, bp_test))


# 2.2. Correction de l’hétéroscédasticité

# * MCO avec écarts-types robustes (White HC1)

# In[38]:


model_multi_hc1 = model_multi.get_robustcov_results(cov_type="HC1")
model_multi_hc1.summary()


# * Moindres carrés pondérés (WLS)

# In[39]:


weights = 1 / df["Surface_m2"]

model_wls = sm.WLS(
    df["Prix_milliers_euros"],
    model_multi.model.exog,
    weights=weights
).fit()

model_wls.summary()


# * Test de Durbin–Watson

# In[40]:


from statsmodels.stats.stattools import durbin_watson

dw_stat = durbin_watson(residuals)
dw_stat


# * Test de Breusch–Godfrey (optional)

# In[41]:


from statsmodels.stats.diagnostic import acorr_breusch_godfrey

bg_test = acorr_breusch_godfrey(model_multi, nlags=2)
labels = ["LM stat", "LM p-value", "F stat", "F p-value"]
dict(zip(labels, bg_test))


# * Correction conjointe : Newey–West (HAC)

# In[42]:


model_multi_nw = model_multi.get_robustcov_results(
    cov_type="HAC",
    maxlags=1
)
model_multi_nw.summary()


# ## 6)Endogénéité et Variables Instrumentale

# 2. Estimation 2SLS (deux étapes)

# In[43]:


from statsmodels.sandbox.regression.gmm import IV2SLS

# Variables exogènes
exog = df[
    ["Surface_m2","Chambres","Annee_construction",
     "Distance_centre_km","Etage","Ascenseur",
     "Revenu_median_quartier","Annee_vente"]
]

# Endogène
endog = df["Qualite_ecole"]

# Instrument exclu
instr = df["Distance_universite"]

# Matrices
X = sm.add_constant(pd.concat([exog, endog], axis=1))
Z = sm.add_constant(pd.concat([exog, instr], axis=1))

iv_model = IV2SLS(df["Prix_milliers_euros"], X, Z).fit()
iv_model.summary()


# 3. Test de pertinence (1ère étape :1ère étape – F = t², instrument faible ou pas ?))
# 

# Règle : si F-stat > 10 ⇒ instrument pas faible.

# In[44]:


import statsmodels.api as sm
import numpy as np
import pandas as pd
from statsmodels.sandbox.regression.gmm import IV2SLS

# Variables
y = df["Prix_milliers_euros"]
endog = "Qualite_ecole"
instr = "Distance_universite"

controls = [
    "Surface_m2","Chambres","Annee_construction",
    "Distance_centre_km","Etage","Ascenseur",
    "Revenu_median_quartier","Annee_vente"
]

# ----- Première étape -----
X_first = sm.add_constant(df[[instr] + controls])
first_stage = sm.OLS(df[endog], X_first).fit()

print(first_stage.summary())

# Test de pertinence : F = t^2
t_instr = first_stage.tvalues[instr]
F_instr = t_instr**2

print("\nTest de pertinence de l'instrument")
print("t-stat =", t_instr)
print("F-stat =", F_instr)


# * Test d’endogénéité (Durbin–Wu–Hausman via control function)

# In[45]:


# Résidus de la première étape
df["vhat"] = first_stage.resid

# Modèle structurel augmenté
X_cf = sm.add_constant(df[[endog] + controls + ["vhat"]])
cf_model = sm.OLS(y, X_cf).fit()

print("\nTest d'endogénéité (Durbin–Wu–Hausman)")
print(cf_model.summary())
print("\nH0: vhat = 0")
print(cf_model.tvalues["vhat"], cf_model.pvalues["vhat"])


# 4. Estimation IV (2SLS) + comparaison avec MCO

# In[46]:


# ----- MCO -----
X_ols = sm.add_constant(df[[endog] + controls])
ols_model = sm.OLS(y, X_ols).fit()

# ----- IV / 2SLS -----
X_iv = sm.add_constant(df[[endog] + controls])
Z_iv = sm.add_constant(df[[instr] + controls])

iv_model = IV2SLS(y, X_iv, Z_iv).fit()

# ----- Tableau de comparaison -----
comparison = pd.DataFrame({
    "OLS_coef": ols_model.params,
    "OLS_se": ols_model.bse,
    "IV_coef": iv_model.params,
    "IV_se": iv_model.bse
})

comparison["Diff_IV_minus_OLS"] = comparison["IV_coef"] - comparison["OLS_coef"]

print("\nComparaison OLS vs IV")
print(comparison.loc[[endog]])


# ## 7) Régularisation : Ridge / Lasso (CV 10-fold) + RMSE

# Variables+ standarisation

# In[47]:


y = df["Prix_milliers_euros"]

X = df[
    ["Surface_m2","Chambres","Annee_construction",
     "Distance_centre_km","Etage","Ascenseur",
     "Qualite_ecole","Revenu_median_quartier","Annee_vente"]
]
scaler = StandardScaler()
X_std = scaler.fit_transform(X)


# In[48]:


X = df[feature_cols].values
y_arr = y.values

X_train, X_test, y_train, y_test = train_test_split(X, y_arr, test_size=0.2, random_state=42)
alphas = np.logspace(-3, 3, 80)

ridge_pipe = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=alphas, cv=10))])
ridge_pipe.fit(X_train, y_train)
ridge_alpha = float(ridge_pipe.named_steps["ridge"].alpha_)
ridge_rmse = float(math.sqrt(mean_squared_error(y_test, ridge_pipe.predict(X_test))))

lasso_pipe = Pipeline([("scaler", StandardScaler()), ("lasso", LassoCV(alphas=alphas, cv=10, max_iter=20000, random_state=42))])
lasso_pipe.fit(X_train, y_train)
lasso_alpha = float(lasso_pipe.named_steps["lasso"].alpha_)
lasso_rmse = float(math.sqrt(mean_squared_error(y_test, lasso_pipe.predict(X_test))))

# OLS benchmark
X_train_ols = sm.add_constant(pd.DataFrame(X_train, columns=feature_cols))
X_test_ols  = sm.add_constant(pd.DataFrame(X_test, columns=feature_cols))
ols_bench = sm.OLS(y_train, X_train_ols).fit()
ols_rmse = float(math.sqrt(mean_squared_error(y_test, ols_bench.predict(X_test_ols))))

rmse_df = pd.DataFrame({
    "Modèle": ["MCO étendu", "Ridge (CV 10-fold)", "Lasso (CV 10-fold)"],
    "RMSE test (k€)": [ols_rmse, ridge_rmse, lasso_rmse],
    "Hyperparamètre": ["-", f"alpha={ridge_alpha:.4g}", f"alpha={lasso_alpha:.4g}"],
})
rmse_df


# In[49]:


# Paths coefficients
scaler = StandardScaler().fit(X_train)
X_train_std = scaler.transform(X_train)

ridge_coefs = np.array([Ridge(alpha=a).fit(X_train_std, y_train).coef_ for a in alphas])
plt.figure(figsize=(8,5))
for j in range(ridge_coefs.shape[1]):
    plt.plot(alphas, ridge_coefs[:, j])
plt.xscale("log")
plt.title("Chemins des coefficients Ridge (variables standardisées)")
plt.xlabel("alpha (log)")
plt.ylabel("Coefficient")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "ridge_paths.png"), dpi=220)
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()
plt.close()

lasso_coefs = np.array([Lasso(alpha=a, max_iter=20000).fit(X_train_std, y_train).coef_ for a in alphas])
plt.figure(figsize=(8,5))
for j in range(lasso_coefs.shape[1]):
    plt.plot(alphas, lasso_coefs[:, j])
plt.xscale("log")
plt.title("Chemins des coefficients Lasso (variables standardisées)")
plt.xlabel("alpha (log)")
plt.ylabel("Coefficient")
plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "lasso_paths.png"), dpi=220)
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()
plt.close()


# ## 8) Prévision 

# 1) Prédiction ponctuelle (Ridge “meilleur modèle”)

# In[50]:


import numpy as np
import pandas as pd

# Observation à prédire (respecter les unités)
new_house = pd.DataFrame([{
    "Surface_m2": 120,
    "Chambres": 3,
    "Annee_construction": 2015,
    "Distance_centre_km": 5,
    "Etage": 1,
    "Ascenseur": 1,                 # Oui = 1
    "Annee_vente": 2023,
    "Qualite_ecole": 7,
    "Revenu_median_quartier": 65,   # 65 000 € -> 65 (en milliers)
    "Distance_universite": 4
}])

# IMPORTANT: même ordre de colonnes que le modèle
X_new = new_house[feature_cols].values

# Prédiction ponctuelle (k€)
pred_point = float(ridge_pipe.predict(X_new)[0])
pred_point


# * prédiction ponctuelle et intervalle de confiance
# 

# In[51]:


from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import numpy as np

B = 2000  # nombre de réplications bootstrap (1000-2000 ok)
preds = np.empty(B)

# Alpha optimal trouvé par CV dans ton ridge_pipe
best_alpha = float(ridge_pipe.named_steps["ridge"].alpha_)

for b in range(B):
    idx = np.random.randint(0, len(X_train), len(X_train))  # bootstrap indices
    Xb = X_train[idx]
    yb = y_train[idx]

    # Refit Ridge avec alpha optimal (on ne refait pas la CV dans la boucle)
    pipe_b = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge", Ridge(alpha=best_alpha))
    ])

    pipe_b.fit(Xb, yb)
    preds[b] = pipe_b.predict(X_new)[0]

# Intervalle 95% par percentiles
lower, upper = np.percentile(preds, [2.5, 97.5])

pred_point, lower, upper


# ## 9) Exports (Excel, ZIP figures, JSON, DOCX, PDF)

# In[ ]:


# ============================================================
# EXPORT FINAL DES RÉSULTATS — VERSION DÉFINITIVE & COMPLÈTE
# ============================================================

import os, json, zipfile
import pandas as pd
import numpy as np

from statsmodels.stats.diagnostic import het_breuschpagan
from statsmodels.stats.stattools import durbin_watson

# ============================================================
# 1. RECALCUL DES DIAGNOSTICS AVANT EXPORT
# ============================================================

# ---------- Breusch–Pagan ----------
bp_test = het_breuschpagan(model_multi.resid, model_multi.model.exog)
bp_res = pd.Series(
    bp_test,
    index=["LM_stat", "LM_pvalue", "F_stat", "F_pvalue"]
)

# ---------- Durbin–Watson ----------
dw = durbin_watson(model_multi.resid)

# ---------- COVID : p-value du Chow ----------
# (on suppose que p_chow a été calculé plus haut)
covid_p = p_chow

# ============================================================
# 2. TABLES DE RÉGRESSION
# ============================================================

def reg_table(res):
    return pd.DataFrame({
        "Coefficient": res.params,
        "Std. Error": res.bse,
        "t-stat": res.tvalues,
        "p-value": res.pvalues
    }).rename_axis("Variable")

t_simple = reg_table(model_simple)
t_multi = reg_table(model_multi)

t_multi_hc1 = pd.DataFrame({
    "Coefficient": model_multi_hc1.params,
    "Std. Error": model_multi_hc1.bse,
    "t-stat": model_multi_hc1.tvalues,
    "p-value": model_multi_hc1.pvalues
}, index=model_multi.params.index).rename_axis("Variable")

t_semilog = reg_table(model_semilog)

t_semilog_hc1 = pd.DataFrame({
    "Coefficient": model_semilog_hc1.params,
    "Std. Error": model_semilog_hc1.bse,
    "t-stat": model_semilog_hc1.tvalues,
    "p-value": model_semilog_hc1.pvalues
}, index=model_semilog.params.index).rename_axis("Variable")

t_loglog = reg_table(model_loglog)

t_loglog_hc1 = pd.DataFrame({
    "Coefficient": model_loglog_hc1.params,
    "Std. Error": model_loglog_hc1.bse,
    "t-stat": model_loglog_hc1.tvalues,
    "p-value": model_loglog_hc1.pvalues
}, index=model_loglog.params.index).rename_axis("Variable")

# ============================================================
# 3. TABLES IV (OPTIONNELLES MAIS RECOMMANDÉES) — VERSION SÛRE
# ============================================================

# ---------- IV 2SLS ----------
if "model_iv" in globals():
    t_iv_2sls = reg_table(model_iv)
elif "iv_model" in globals():
    t_iv_2sls = reg_table(iv_model)
elif "model_iv2sls" in globals():
    t_iv_2sls = reg_table(model_iv2sls)
else:
    t_iv_2sls = pd.DataFrame(
        {"IV_2SLS": ["not computed"]},
        index=["status"]
    )

# ---------- Premier stade ----------
if "first_stage" in globals():
    t_first_stage = reg_table(first_stage)
else:
    t_first_stage = pd.DataFrame(
        {"First_stage": ["not computed"]},
        index=["status"]
    )

# ---------- Durbin–Wu–Hausman ----------
# ---------- Durbin–Wu–Hausman (méthode control function) ----------

if "first_stage" in globals():
    # Résidus du premier stade
    df["vhat"] = first_stage.resid

    # Modèle structurel augmenté
    X_cf = sm.add_constant(df[[endog] + controls + ["vhat"]])
    cf_model = sm.OLS(y, X_cf).fit()

    dwh_stat = cf_model.tvalues["vhat"]
    dwh_p = cf_model.pvalues["vhat"]

    dwh_res = pd.Series(
        {"DWH_t_stat": dwh_stat, "DWH_pvalue": dwh_p}
    ).to_frame("value")
else:
    dwh_res = pd.Series(
        {"DWH": "not computed"}
    ).to_frame("value")



# ============================================================
# 4. AUTRES TABLES
# ============================================================

bp_export = bp_res.to_frame("value")

autres_tests = pd.Series({
    "Durbin_Watson": dw,
    "COVID_break_pvalue": covid_p
}).to_frame("value")

# ============================================================
# 5. EXPORT EXCEL
# ============================================================

with pd.ExcelWriter(TABLES_XLSX) as writer:
    desc.to_excel(writer, sheet_name="Descriptives")
    corr.to_excel(writer, sheet_name="Correlation")
    vif_df.to_excel(writer, sheet_name="VIF", index=False)

    t_simple.to_excel(writer, sheet_name="OLS_simple")
    t_multi.to_excel(writer, sheet_name="OLS_multiple")
    t_multi_hc1.to_excel(writer, sheet_name="OLS_multiple_HC1")

    t_semilog.to_excel(writer, sheet_name="SemiLog_lnPrix")
    t_semilog_hc1.to_excel(writer, sheet_name="SemiLog_lnPrix_HC1")

    t_loglog.to_excel(writer, sheet_name="LogLog_lnPrix")
    t_loglog_hc1.to_excel(writer, sheet_name="LogLog_lnPrix_HC1")

    # IV
    t_first_stage.to_excel(writer, sheet_name="IV_FirstStage")
    t_iv_2sls.to_excel(writer, sheet_name="IV_2SLS")
    dwh_res.to_excel(writer, sheet_name="DWH_test")

    rmse_df.to_excel(writer, sheet_name="RMSE_test", index=False)

    bp_export.to_excel(writer, sheet_name="Breusch_Pagan")
    autres_tests.to_excel(writer, sheet_name="Autres_tests")

# ============================================================
# MOYENNE ANNUELLE DES PRIX + FIGURE ASSOCIÉE
# ============================================================

mean_by_year = (
    df.groupby("Annee_vente")["Prix_milliers_euros"]
      .mean()
      .reset_index()
)

mean_by_year.to_csv(MEAN_CSV, index=False)

# ----- Figure : évolution du prix moyen -----
plt.figure(figsize=(8, 5))
plt.plot(
    mean_by_year["Annee_vente"],
    mean_by_year["Prix_milliers_euros"],
    marker="o",
    linewidth=2
)

plt.xlabel("Année de vente")
plt.ylabel("Prix moyen (en milliers d'euros)")
plt.title("Évolution du prix moyen par année de vente (2015–2023)")
plt.grid(True)

plt.tight_layout()
plt.savefig(os.path.join(FIG_DIR, "prix_moyen_par_annee.png"), dpi=220)
plt.savefig(FIGURES_DIR / f"figure_{plt.gcf().number}.png", dpi=300, bbox_inches='tight')
plt.close()
plt.close()

# ============================================================
# 6. EXPORT FIGURES
# ============================================================

with zipfile.ZipFile(FIG_ZIP, "w", compression=zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(FIG_DIR)):
        if fn.lower().endswith(".png"):
            z.write(os.path.join(FIG_DIR, fn), arcname=f"figures/{fn}")

# ============================================================
# 7. EXPORT DONNÉES COMPLÉMENTAIRES
# ============================================================

mean_by_year = (
    df.groupby("Annee_vente")["Prix_milliers_euros"]
      .mean()
      .reset_index()
)
mean_by_year.to_csv(MEAN_CSV, index=False)

best_model_safe = best_model_name if "best_model_name" in globals() else "Ridge"

summary = {
    "n_obs": int(len(df)),
    "periode": [
        int(df["Annee_vente"].min()),
        int(df["Annee_vente"].max())
    ],
    "diagnostics": {
        "Breusch_Pagan": bp_res.to_dict(),
        "Durbin_Watson": dw,
        "COVID_break_pvalue": covid_p
    },
    "IV_tests": {
    "DWH_pvalue": dwh_p if "dwh_p" in globals() else "not computed"

    },
    "performances_prediction": {
        "RMSE_test": {
            "OLS_multiple": float(ols_rmse),
            "Ridge": float(ridge_rmse),
            "Lasso": float(lasso_rmse)
        }
    },
    "regularisation": {
        "Ridge_alpha": float(ridge_alpha),
        "Lasso_alpha": float(lasso_alpha),
        "best_model": best_model_safe
    },
    "prediction_house": {
        "price_kEUR": float(pred_point),
        "interval_95_kEUR": [float(lower), float(upper)]
    }
}

with open(SUMMARY_JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print("✅ EXPORT FINAL TERMINÉ (version robuste)")
print(f"📊 Tables Excel : {TABLES_XLSX}")
print(f"🖼️ Figures ZIP  : {FIG_ZIP}")
print(f"📈 Moyennes CSV : {MEAN_CSV}")
print(f"🧾 Résumé JSON  : {SUMMARY_JSON}")

