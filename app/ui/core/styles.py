import streamlit as st


def apply_custom_css():
    st.markdown(
        """
        <style>
        /* --- FONTE GLOBAL --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* --- VARIÁVEIS (PALETA COMPLETA) --- */
        :root {
            /* Cores da Marca */
            --primary-dark: #0f172a;   /* Azul Petróleo Escuro (Texto Forte) */
            --primary-light: #334155;  /* Cinza Azulado (Texto Suave) */
            --accent: #d97706;         /* Bronze/Dourado (Cor do Robô) */
            --accent-bg: #fffbeb;      /* Fundo Creme suave */
            
            /* UI Geral */
            --bg-page: #f8fafc;        /* Branco Gelo */
            --card-bg: #ffffff;        /* Branco Puro */
            --text-body: #475569;      /* Cinza Médio */
            
            /* Status do Sistema (Dashboard) */
            --success: #22c55e;        /* Verde Sucesso */
            --warning: #f59e0b;        /* Amarelo Alerta */
            --danger: #ef4444;         /* Vermelho Erro */
        }

        /* --- RESETS GERAIS --- */
        [data-testid="stAppViewContainer"] { background-color: var(--bg-page); }
        [data-testid="stHeader"] { background-color: transparent; }
        [data-testid="stSidebar"] { display: none; }
        
        h1, h2, h3, p, div, span, button { font-family: 'Inter', sans-serif; }
        
        .block-container {
            padding-top: 3rem;
            max-width: 1200px;
        }

        /* --- COMPONENTES: LANDING PAGE --- */
        
        /* Hero Section */
        .hero-container { padding: 4rem 0; animation: fadeIn 1.0s ease-in; }
        
        .hero-tag {
            background-color: var(--accent-bg);
            color: var(--accent);
            padding: 6px 14px;
            border-radius: 99px;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            display: inline-block;
            margin-bottom: 1.5rem;
            border: 1px solid #fcd34d;
        }

        .hero-title {
            font-size: 3.5rem;
            font-weight: 800;
            line-height: 1.1;
            margin-bottom: 1.5rem;
            background: -webkit-linear-gradient(120deg, var(--primary-dark), var(--primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .hero-subtitle {
            font-size: 1.2rem;
            color: var(--text-body);
            line-height: 1.6;
            margin-bottom: 2.5rem;
            font-weight: 400;
            max-width: 580px;
        }

        /* Features Cards (Landing) */
        .feature-card {
            background: var(--card-bg);
            padding: 2rem;
            border-radius: 20px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
            transition: all 0.3s ease;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: flex-start;
        }
        .feature-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            border-color: var(--accent);
        }

        .icon-box {
            background: var(--accent-bg);
            color: var(--accent);
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.4rem;
            margin-bottom: 1.2rem;
        }
        
        .card-title {
            font-size: 1.1rem;
            font-weight: 700;
            color: var(--primary-dark);
            margin-bottom: 0.5rem;
        }

        .card-text {
            font-size: 0.95rem;
            color: var(--text-body);
            line-height: 1.5;
        }

        .footer-container {
            border-top: 1px solid #e2e8f0;
            margin-top: 5rem;
            padding-top: 2rem;
            text-align: center;
        }
        .footer-text { color: #94a3b8; font-size: 0.85rem; }

        /* Popover mais discreto */
        [data-testid="stPopover"] > button {
            padding: 4px 8px !important;
            font-size: 1.1rem !important;
        }

        /* --- COMPONENTES: APP INTERNO (DASHBOARD) --- */

        /* Tabs do Streamlit */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: white;
            padding: 10px;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 1rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 8px;
            font-weight: 600;
            color: var(--primary-dark);
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--accent-bg) !important;
            color: var(--accent) !important;
        }

        [data-testid="stMetric"] {
            background-color: white; /* Fundo Branco */
            padding: 15px;           /* Espaçamento interno */
            border-radius: 12px;     /* Bordas arredondadas */
            border: 1px solid #e2e8f0; /* Borda cinza suave */
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); /* Sombra leve */
            text-align: center;      /* Centraliza o texto */
        }
        .stStatusWidget {
            display: none !important;
        }
        
        /* Esconde o container do spinner */
        div[data-testid="stStatusWidget"] {
            display: none !important;
        }
        
        /* Esconde especificamente o emoji/icon */
        div[data-testid="stStatusWidget"] svg,
        div[data-testid="stStatusWidget"] .stSpinner {
            display: none !important;
        }
        
        /* Esconde o elemento "Running..." */
        .stAlert[data-baseweb="notification"] {
            display: none !important;
        }
        
        /* Esconde qualquer spinner do Streamlit */
        .streamlit-spinner {
            display: none !important;
        }
        
        /* Esconde o texto "Running" no canto */
        section[data-testid="stSidebar"] .stSpinner,
        section[data-testid="stSidebar"] .stAlert {
            display: none !important;
        }
        /* Metric Cards */
        .custom-metric-card {
            background: white;
            padding: 20px;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.02);
            text-align: center;
            height: 100%;
        }
        .metric-label { 
            font-size: 0.8rem; 
            color: #64748b; 
            margin-bottom: 8px; 
            text-transform: uppercase; 
            letter-spacing: 0.8px;
            font-weight: 600;
        }
        .metric-value { 
            font-size: 1.8rem; 
            font-weight: 800; 
            color: var(--primary-dark); 
            line-height: 1;
        }
        .metric-delta { 
            font-size: 0.85rem; 
            font-weight: 600; 
            margin-top: 8px; 
            display: inline-block;
            padding: 2px 8px;
            border-radius: 6px;
        }
        
        .status-good { color: #15803d; background-color: #dcfce7; }
        .status-warn { color: #b45309; background-color: #fef3c7; }
        .status-bad { color: #b91c1c; background-color: #fee2e2; }

        /* --- RESPONSIVIDADE --- */
        @media (max-width: 768px) {
            .hero-title { font-size: 2.5rem; }
            .hero-container { text-align: center; }
            .hero-subtitle { margin: 0 auto 2rem auto; }
            .block-container { padding-top: 1rem; }
        }
        
        @keyframes fadeIn {
            0% { opacity: 0; transform: translateY(20px); }
            100% { opacity: 1; transform: translateY(0); }
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
