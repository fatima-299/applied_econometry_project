Python Script Overview (Projet_Immobilier_Statistique_SAYED_Fatima.py)
The file Projet_Immobilier_Statistique_SAYED_Fatima.py is a stand-alone script that reproduces the entire notebook workflow and generates all tables and figures used in the report.

1️⃣ Descriptive Analysis
Summary statistics, skewness, kurtosis
Histograms and boxplots (Appendix B.1)

2️⃣ Correlation Analysis
Pearson correlation matrix
Heatmap visualization (Appendix B.2)

3️⃣ Econometric Models
Simple OLS
Multiple OLS
Semi-log and log-log specifications
Robust standard errors (HC1)

4️⃣ Econometric Diagnostics
Multicollinearity (VIF)
Significance tests (t-tests, F-tests)
Heteroskedasticity (Breusch–Pagan)
Autocorrelation (Durbin–Watson, Breusch–Godfrey)
Structural break (COVID-19 interactions and Chow test)

5️⃣ Endogeneity
Instrumental Variables (2SLS)
First-stage regression
Durbin–Wu–Hausman test (control function approach)
OLS vs IV comparison

6️⃣ Regularization
Ridge and Lasso with standardized variables
10-fold cross-validation
Coefficient paths (Appendix B.4)
Predictive performance comparison (RMSE)

7️⃣ Forecasting
Point prediction using Ridge
95% confidence interval via bootstrap
Discussion of prediction reliability

8️⃣ Automated Exports
Excel tables
Figures ZIP archive
CSV and JSON summary files

▶️ How to Run the Project

Requirements
Python ≥ 3.9 with the following packages:

pip install pandas numpy matplotlib statsmodels scikit-learn scipy python-docx reportlab

Run the script
python Projet_Immobilier_Statistique_SAYED_Fatima.py


All outputs (tables, figures, summaries) will be generated automatically.

📎 Link with the Report
Appendix A (Tables) → tables_resultats.xlsx
Appendix B (Figures) → Figures_projet_M2.zip
Appendix C (Code) →  GitHub link
Main report → Rapport_final_Analyse_Prix_Immobiliers_SAYED_Fatima.docx
Each figure and table is explicitly referenced and interpreted in the written report.
