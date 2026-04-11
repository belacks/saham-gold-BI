├── data/
│   ├── raw/           # 'Data Historis GOLD.csv' di sini (Immutable)
│   └── processed/     # Data hasil cleaning/feature engineering
├── docs/              # Tempat naruh Proposal , Laporan, Timeline 
├── notebooks/         # Jupyter notebooks buat EDA awal & eksperimen (1 notebook per orang/task)
├── src/               # Script python modular (ETL pipeline, utils)
├── dashboard/         # File untuk BI Dashboard (misal file .pbix, atau script Streamlit)
├── .gitignore         # Wajib! Ignore data besar, env, dan file cache
├── requirements.txt   # Dependencies (pandas, jupyter, matplotlib, dll)
└── README.md          # Penjelasan project, cara setup env, dan pembagian Jobdesk