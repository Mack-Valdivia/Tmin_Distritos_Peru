# Tmin_Distritos_Peru

#🧊 Tmin Perú — Análisis de Temperatura Mínima & Riesgo de Friaje

Autor: Mack-Valdivia

Repo: https://github.com/Mack-Valdivia/Tmin_Distritos_Peru

Proyecto geoespacial para mapear y analizar la temperatura mínima (Tmin) en el Perú, identificar zonas críticas de friaje y proponer políticas públicas con enfoque territorial. Incluye dashboard Streamlit y notebook reproducible.

#🎯 Objetivos

Principal: caracterizar la variabilidad espacial de la Tmin a nivel distrital y detectar zonas de alto riesgo (heladas y oleadas de frío).

Específicos:

Calcular estadísticas zonales por distrito (≥6 métricas + p5 personalizada).

Identificar patrones geográficos y elaborar rankings (más fríos / más cálidos).

Desarrollar visualizaciones científicas y un mapa coroplético nacional.

Proponer medidas de política pública con costos aproximados y KPIs.


#🗂️ Estructura del repositorio

Tmin_Distritos_Peru/
├── app/                      # Aplicación Streamlit
│   └── app.py               # Dashboard principal (auto-descarga datos si faltan)
├── data/                     # Datos fuente (vacío en GitHub; se llenan en runtime)
│   └── get_data.py          # (opcional) Descarga por script local
├── notebooks/                # Análisis y EDA
│   └── TempDistritos_AnalisisPerú.ipynb
├── outputs/                  # Figuras y CSVs generados por el flujo
├── requirements.txt          # Dependencias del proyecto
├── README.md                 # Este documento
└── .gitignore














