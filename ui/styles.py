import streamlit as st

def inject_styles():
    """
    Injects custom CSS to style the Streamlit interface into a modern,
    visually-impressive financial analytics dashboard.
    """
    css = """
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    <style>
        /* Base typography */
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }
        
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            letter-spacing: -0.02em;
        }
        
        /* Glassmorphism Card Container */
        .glass-card {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.15);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }
        
        .glass-card:hover {
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 12px 40px 0 rgba(0, 0, 0, 0.25);
            transform: translateY(-2px);
        }
        
        /* Metric Card specific styling */
        .metric-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 12px;
            padding: 16px 20px;
            text-align: left;
            transition: all 0.2s ease;
        }
        
        .metric-card:hover {
            border-color: rgba(255, 255, 255, 0.12);
            transform: scale(1.02);
        }
        
        .metric-title {
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 8px;
            font-weight: 500;
        }
        
        .metric-value {
            font-size: 1.8rem;
            font-weight: 700;
            font-family: 'Outfit', sans-serif;
            color: #ffffff;
            margin-bottom: 4px;
        }
        
        .metric-subtext {
            font-size: 0.75rem;
            color: rgba(255, 255, 255, 0.4);
        }
        
        /* Recommendation Badges with subtle glows */
        .badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 8px 16px;
            border-radius: 30px;
            font-weight: 700;
            font-size: 1.1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-family: 'Outfit', sans-serif;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .badge-safe-buy {
            background-color: rgba(34, 197, 94, 0.12);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
            box-shadow: 0 0 15px rgba(34, 197, 94, 0.15);
        }
        
        .badge-moderate-risk {
            background-color: rgba(245, 158, 11, 0.12);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
            box-shadow: 0 0 15px rgba(245, 158, 11, 0.15);
        }
        
        .badge-high-risk {
            background-color: rgba(239, 68, 68, 0.12);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.15);
        }
        
        /* Risk signals */
        .risk-flag-container {
            display: flex;
            align-items: center;
            padding: 10px 14px;
            background: rgba(239, 68, 68, 0.06);
            border-left: 4px solid #ef4444;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        
        .risk-flag-text {
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.9);
            margin-left: 10px;
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.01);
        }
        
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        
        /* Title styling */
        .dashboard-title {
            background: linear-gradient(90deg, #3b82f6 0%, #8b5cf6 50%, #ec4899 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 800;
            font-size: 2.8rem;
            letter-spacing: -0.03em;
            margin-bottom: 10px;
        }
        
        .dashboard-subtitle {
            font-size: 1.1rem;
            color: rgba(255, 255, 255, 0.6);
            margin-bottom: 30px;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
