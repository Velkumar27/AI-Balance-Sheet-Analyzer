import streamlit as st
import os
import io
import json
import pandas as pd
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Set page config FIRST before any other streamlit commands
st.set_page_config(
    page_title="AI Financial Balance Sheet Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

from ingestion.excel_parser import ExcelParser
from ingestion.chunker import ParentChildChunker
from embeddings.embedder import OpenAIEmbedder
from retrieval.faiss_store import FAISSStore
from retrieval.parent_child_retriever import ParentChildRetriever
from analytics.metric_extractor import MetricExtractor
from analytics.ratio_calculator import RatioCalculator
from analytics.trend_analyzer import TrendAnalyzer
from analytics.risk_scorer import RiskScorer
from analytics.llm_analyzer import LLMAnalyzer
from prompts.chat_prompts import build_chat_prompt

from ui.styles import inject_styles
from ui.components import (
    render_recommendation_panel,
    render_kpi_cards,
    render_risk_flags,
    render_stock_strength_index,
    render_ratio_table,
    render_extracted_metrics,
    generate_pdf_report
)
from ui.charts import render_trend_chart, render_radar_chart, render_waterfall_chart

# Inject Premium UI CSS Styles
inject_styles()

# Define Mock Data Generator for Demo Mode
def load_demo_data() -> bytes:
    """Generates a mock multi-sheet financial Excel file in-memory for testing."""
    output = io.BytesIO()
    
    # Create mock sheets using pandas ExcelWriter
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # 1. Income Statement (P&L)
        pl_data = {
            "Particulars": [
                "Revenue from Operations", 
                "Cost of Materials Consumed", 
                "Employee Benefits Expense", 
                "EBITDA", 
                "Depreciation and Amortization",
                "Finance Costs", 
                "Profit Before Tax (PBT)",
                "Tax Expense", 
                "Net Profit for the Year (PAT)"
            ],
            "FY 2024": [1000.0, 450.0, 150.0, 400.0, 50.0, 30.0, 320.0, 80.0, 240.0],
            "FY 2025": [1250.0, 550.0, 180.0, 520.0, 55.0, 28.0, 437.0, 109.0, 328.0],
            "FY 2026": [1600.0, 680.0, 220.0, 700.0, 60.0, 25.0, 615.0, 154.0, 461.0]
        }
        pd.DataFrame(pl_data).to_excel(writer, sheet_name="Income Statement", index=False)
        
        # 2. Balance Sheet
        bs_data = {
            "Particulars": [
                "Total Equity Share Capital",
                "Reserves and Surplus",
                "Total Shareholders Equity",
                "Long Term Borrowings",
                "Short Term Borrowings",
                "Total Debt",
                "Total Liabilities",
                "Property, Plant & Equipment",
                "Current Assets",
                "Cash and Cash Equivalents",
                "Total Assets"
            ],
            "FY 2024": [100.0, 700.0, 800.0, 200.0, 100.0, 300.0, 1100.0, 600.0, 500.0, 150.0, 1400.0],
            "FY 2025": [100.0, 920.0, 1020.0, 150.0, 100.0, 250.0, 1270.0, 650.0, 620.0, 180.0, 1720.0],
            "FY 2026": [100.0, 1220.0, 1320.0, 100.0, 80.0, 180.0, 1500.0, 700.0, 800.0, 250.0, 2100.0]
        }
        pd.DataFrame(bs_data).to_excel(writer, sheet_name="Balance Sheet", index=False)
        
        # 3. Cash Flow Statement
        cf_data = {
            "Particulars": [
                "Cash flow from operating activities",
                "Net Profit Before Tax",
                "Depreciation adjustment",
                "Operating cash flow before working capital adjustments",
                "Operating Cash Flow",
                "Capital Expenditures (Capex)",
                "Cash flow from investing activities",
                "Repayment of Borrowings",
                "Cash flow from financing activities",
                "Net Cash Flow"
            ],
            "FY 2024": [320.0, 320.0, 50.0, 370.0, 280.0, -100.0, -120.0, -50.0, -80.0, 80.0],
            "FY 2025": [437.0, 437.0, 55.0, 492.0, 380.0, -120.0, -150.0, -50.0, -78.0, 152.0],
            "FY 2026": [615.0, 615.0, 60.0, 675.0, 520.0, -150.0, -190.0, -70.0, -95.0, 235.0]
        }
        pd.DataFrame(cf_data).to_excel(writer, sheet_name="Cash Flow", index=False)
        
    output.seek(0)
    return output.getvalue()


# Initialize core services in session state
if "faiss_store" not in st.session_state:
    st.session_state.faiss_store = FAISSStore()
if "companies_data" not in st.session_state:
    st.session_state.companies_data = {}  # key: company_name, value: parsed metrics, ratios, etc.
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # List of chat messages

# Sidebar Setup
st.sidebar.markdown("""
<div style='text-align: center; padding-bottom: 20px;'>
    <h2 style='font-family: Outfit; color: #60a5fa; margin-bottom: 0;'>FinSight AI</h2>
    <span style='font-size: 0.85rem; color: rgba(255,255,255,0.4);'>Institutional-Grade Equity Research</span>
</div>
""", unsafe_allow_html=True)

# 1. API Configuration Status
api_key = os.environ.get("OPENAI_API_KEY", "")
api_key_valid = bool(api_key and "your_openai_api_key" not in api_key and api_key.strip() != "")

st.sidebar.subheader("🔑 API Status")
if api_key_valid:
    st.sidebar.success("OpenAI API Key loaded from .env")
else:
    st.sidebar.error("OpenAI API Key not configured")
    st.sidebar.info("Please set `OPENAI_API_KEY` in your `.env` file and restart the application.")

# 2. File Uploads
st.sidebar.subheader("📁 Workbook Ingestion")
uploaded_files = st.sidebar.file_uploader(
    "Upload Financial Workbook (.xlsx)",
    type=["xlsx"],
    accept_multiple_files=True,
    help="Upload multi-sheet Excel balance sheets, income statements, cash flow statements, etc."
)

# Demo Mode Option
st.sidebar.markdown("<div style='text-align: center; margin: 10px 0;'>or</div>", unsafe_allow_html=True)
demo_btn = st.sidebar.button("💡 Load Demo Unilever Mock Data", use_container_width=True)

# Action button to trigger parsing and RAG indexing
analyze_btn = st.sidebar.button("🚀 Analyze Workbooks", type="primary", use_container_width=True)

# Reset Button
if st.sidebar.button("🗑️ Clear Vector Index & Uploads", use_container_width=True):
    st.session_state.faiss_store.clear()
    st.session_state.companies_data = {}
    st.session_state.chat_history = []
    st.success("Vector database index cleared.")
    st.rerun()

# ----------------------------------------------------
# Main Analysis Pipeline Execution
# ----------------------------------------------------
if analyze_btn or (demo_btn and not st.session_state.companies_data):
    if not api_key_valid:
        st.error("Please supply a valid OpenAI API key in the `.env` file to continue.")
    else:
        # Assemble workbooks to process
        workbooks_to_process = []
        if demo_btn:
            workbooks_to_process.append(("Hindustan_Unilever_Demo", load_demo_data()))
        elif uploaded_files:
            for f in uploaded_files:
                workbooks_to_process.append((f.name, f.read()))
        else:
            st.warning("Please upload at least one Excel workbook or load the Demo Unilever Data.")
            workbooks_to_process = []
            
        if workbooks_to_process:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Setup Embedder
            embedder = OpenAIEmbedder()
            chunker = ParentChildChunker(target_chunk_tokens=200)
            
            for index, (filename, file_bytes) in enumerate(workbooks_to_process):
                status_text.text(f"Parsing Excel sheets for {filename}...")
                progress_bar.progress(int((index / len(workbooks_to_process)) * 50))
                
                # 1. Parsing workbook
                excel_data = ExcelParser.parse_workbook(file_bytes, filename)
                company_name = excel_data["workbook_name"]
                
                # 2. Extract metrics (Deterministic + LLM Fallback)
                status_text.text(f"Extracting fundamental financial KPIs for {company_name}...")
                openai_client = embedder._get_client() # retrieve openai client
                metric_extractor = MetricExtractor(openai_client=openai_client)
                metrics_data = metric_extractor.extract_metrics(excel_data["sheets"])
                
                # 3. Calculate Ratios
                status_text.text(f"Computing investment ratios for {company_name}...")
                ratios_data = RatioCalculator.calculate_ratios(metrics_data)
                
                # 4. Trend Analysis
                status_text.text(f"Executing historical trend analyses for {company_name}...")
                trend_data = TrendAnalyzer.analyze_trends(metrics_data)
                
                # 5. Risk & Stock Strength Index calculation
                status_text.text(f"Formulating Risk Scorer parameters for {company_name}...")
                strength_data = RiskScorer.calculate_strength_score(metrics_data, ratios_data, trend_data)
                
                # 6. Embed Parent-Child chunks and populate Vector DB
                status_text.text(f"Generating vectors and indexing {company_name} into FAISS...")
                all_child_chunks = []
                parent_docs = {}
                
                for s_name, s_content in excel_data["sheets"].items():
                    parent_doc, child_chunks = chunker.chunk_sheet(s_content["markdown"], company_name, s_name)
                    all_child_chunks.extend(child_chunks)
                    parent_docs[parent_doc["id"]] = parent_doc
                    
                # Create embeddings
                child_texts = [chunk["text"] for chunk in all_child_chunks]
                embeddings = embedder.embed_documents(child_texts)
                
                # Save to vector store
                st.session_state.faiss_store.add_documents(all_child_chunks, embeddings, parent_docs)
                
                # 7. LLM recommendation panel and Investment Thesis Synthesis
                status_text.text(f"Orchestrating CFA Recommendation panel for {company_name}...")
                llm_analyzer = LLMAnalyzer()
                rec_data = llm_analyzer.generate_recommendation_panel(
                    company_name=company_name,
                    sheets_dict=excel_data["sheets"],
                    metrics_data=metrics_data,
                    ratios_data=ratios_data,
                    trend_data=trend_data,
                    strength_data=strength_data
                )
                
                status_text.text(f"Synthesizing complete Research Thesis for {company_name}...")
                thesis = llm_analyzer.analyze_company_statements(company_name, excel_data["sheets"])
                rec_data["investment_thesis"] = thesis  # Bind detailed thesis
                
                # Cache results in session state
                st.session_state.companies_data[company_name] = {
                    "sheets": excel_data["sheets"],
                    "metrics": metrics_data,
                    "ratios": ratios_data,
                    "trends": trend_data,
                    "strength": strength_data,
                    "recommendation": rec_data
                }
                
            progress_bar.progress(100)
            status_text.text("Ingestion completed! Loading dashboard panels...")
            progress_bar.empty()
            status_text.empty()
            
            # Save local index
            st.session_state.faiss_store.save()
            st.success("Successfully parsed, indexed, and evaluated all company workbooks!")


# ----------------------------------------------------
# Main Dashboard UI Display
# ----------------------------------------------------
st.markdown("<div class='dashboard-title'>AI Financial Balance Sheet Analyzer</div>", unsafe_allow_html=True)
st.markdown("<div class='dashboard-subtitle'>Fundamental Equity Research, Stock Strength Scoring, & Conversational Q&A</div>", unsafe_allow_html=True)

if not st.session_state.companies_data:
    st.info("👈 Complete the API configuration, upload Excel workbooks (.xlsx), and click 'Analyze Workbooks' in the sidebar to begin analysis.")
    
    # Beautiful visual dashboard cards placeholders
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <div style="font-size: 3rem;">📊</div>
            <h3 style="margin-top: 10px; color: #fff;">1. Smart Workbook Ingestion</h3>
            <p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); line-height: 1.5;">
                Upload Balance Sheets, P&Ls, and Cash Flows. The parser automatically structures grids into aligned markdown tables.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <div style="font-size: 3rem;">⚖️</div>
            <h3 style="margin-top: 10px; color: #fff;">2. Fundamental Scoring</h3>
            <p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); line-height: 1.5;">
                Computes Stock Strength Indexes out of 100, detects financial anomalies, and yields Safe Buy / Moderate Risk / High Risk recommendations.
            </p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="glass-card" style="text-align: center;">
            <div style="font-size: 3rem;">💬</div>
            <h3 style="margin-top: 10px; color: #fff;">3. Conversational RAG Chat</h3>
            <p style="font-size: 0.9rem; color: rgba(255,255,255,0.6); line-height: 1.5;">
                Ask details about debt maturities, margins, cash conversions, and get answers that cite spreadsheets and sections exactly.
            </p>
        </div>
        """, unsafe_allow_html=True)
else:
    company_names = list(st.session_state.companies_data.keys())
    
    # Handle single or multi-company navigation
    if len(company_names) > 1:
        company_select_col, mode_select_col = st.columns([2, 1])
        with company_select_col:
            selected_company = st.selectbox("🎯 Target Entity under Review", company_names)
        with mode_select_col:
            view_mode = st.radio("🖥️ Mode", ["Individual Dashboard", "Multi-Company Compare"], horizontal=True)
    else:
        selected_company = company_names[0]
        view_mode = "Individual Dashboard"
        
    st.write("")
    
    # ----------------------------------------------------
    # VIEW MODE 1: Individual Dashboard
    # ----------------------------------------------------
    if view_mode == "Individual Dashboard":
        # Extract selected company data
        comp_data = st.session_state.companies_data[selected_company]
        sheets = comp_data["sheets"]
        metrics = comp_data["metrics"]
        ratios = comp_data["ratios"]
        trends = comp_data["trends"]
        strength = comp_data["strength"]
        rec = comp_data["recommendation"]
        
        # Tabs for Individual dashboard
        tab_summary, tab_details, tab_charts, tab_chat, tab_raw = st.tabs([
            "📋 Executive thesis & rating",
            "📊 Core KPIs & Ratios",
            "📈 Interactive Trend Charts",
            "💬 Conversational Analyst Chat",
            "📁 Raw Structured Sheets"
        ])
        
        # TAB 1: Executive thesis
        with tab_summary:
            st.subheader(f"Investment Evaluation Brief: {selected_company}")
            render_recommendation_panel(rec, strength, selected_company)
            
            st.write("")
            st.subheader("⚠️ Core Warnings & Risk Alerts")
            render_risk_flags(strength)
            
            # PDF Export Option
            st.write("")
            pdf_bytes = generate_pdf_report(selected_company, rec, strength, ratios, metrics)
            st.download_button(
                label="📥 Export Complete Investment Brief PDF",
                data=pdf_bytes,
                file_name=f"{selected_company}_Investment_Brief.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
        # TAB 2: KPIs & Ratios
        with tab_details:
            st.subheader("Fundamental financial KPIs")
            render_kpi_cards(metrics)
            
            st.write("")
            col_l, col_r = st.columns([3, 2])
            with col_l:
                st.subheader("Computed Financial Ratios")
                render_ratio_table(ratios, metrics["years"])
            with col_r:
                st.subheader("Stock Strength Score Breakdown")
                render_stock_strength_index(strength)
                
            st.write("")
            st.subheader("Extracted Core Statement Values (Aligned Across Years)")
            render_extracted_metrics(metrics)
            
        # TAB 3: Trend Charts
        with tab_charts:
            st.subheader("Interactive Statement Growth & Leverage Trends")
            render_trend_chart(metrics)
            
            st.write("")
            col_chart_l, col_chart_r = st.columns(2)
            with col_chart_l:
                render_radar_chart(strength)
            with col_chart_r:
                render_waterfall_chart(metrics)
                
        # TAB 4: Conversational Chat
        with tab_chat:
            st.subheader("💬 Ask questions about the target company's financials")
            st.markdown("""
            Ask anything about the company's balance sheet, leverage, liquidity, or growth. 
            The system retrieves corresponding spreadsheets and swaps child chunks with the complete tables for accurate answers.
            """)
            
            # Display past messages
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if "sources" in message and message["sources"]:
                        with st.expander("📚 Retrieved Source Sheets"):
                            for src in message["sources"]:
                                st.markdown(f"- **[Sheet: {src['sheet']}]** (Workbook: {src['workbook']}, Relevance: {src['score']:.1%})")
                                
            # Capture User Query
            if user_query := st.chat_input("Ask a financial question (e.g. 'Is the company's debt growth a major risk?'):"):
                # Display user message
                with st.chat_message("user"):
                    st.markdown(user_query)
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                
                # Retrieval and Answer Synthesis
                with st.chat_message("assistant"):
                    with st.spinner("Analyzing spreadsheets..."):
                        # RAG Swapping Pipeline
                        retriever = ParentChildRetriever(st.session_state.faiss_store, OpenAIEmbedder())
                        retrieved_sheets = retriever.retrieve(user_query, top_k=3)
                        
                        sources = []
                        context_str = ""
                        for item in retrieved_sheets:
                            context_str += item["text"] + "\n\n"
                            sources.append({
                                "sheet": item["sheet_name"],
                                "workbook": item["workbook_name"],
                                "score": item["score"]
                            })
                            
                        # Build message prompt
                        openai_client = OpenAIEmbedder()._get_client()
                        messages = build_chat_prompt(user_query, context_str, st.session_state.chat_history[:-1])
                        
                        try:
                            # Call LLM
                            response = openai_client.chat.completions.create(
                                model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                                messages=messages,
                                temperature=0.1
                            )
                            answer = response.choices[0].message.content
                            
                            st.markdown(answer)
                            st.session_state.chat_history.append({
                                "role": "assistant",
                                "content": answer,
                                "sources": sources
                            })
                            
                            if sources:
                                with st.expander("📚 Retrieved Source Sheets"):
                                    for src in sources:
                                        st.markdown(f"- **[Sheet: {src['sheet']}]** (Workbook: {src['workbook']}, Relevance: {src['score']:.1%})")
                        except Exception as e:
                            st.error(f"Error answering question: {e}")
                            
        # TAB 5: Raw Sheets
        with tab_raw:
            st.subheader("Raw Markdown Table Output (Preserving Columns & Struct)")
            selected_sheet_name = st.selectbox("Select Sheet to view", list(sheets.keys()))
            if selected_sheet_name:
                st.markdown(f"```markdown\n{sheets[selected_sheet_name]['markdown']}\n```")
                
    # ----------------------------------------------------
    # VIEW MODE 2: Multi-Company Comparison (Bonus)
    # ----------------------------------------------------
    elif view_mode == "Multi-Company Compare":
        st.subheader("⚔️ Side-by-Side Financial Comparison")
        
        # Build comparison grid
        comp_records = []
        for name, data in st.session_state.companies_data.items():
            metrics = data["metrics"]
            ratios = data["ratios"]
            strength = data["strength"]
            rec = data["recommendation"]
            
            # Fetch latest indicators
            latest_idx = -1
            latest_year = metrics["years"][latest_idx]
            
            rev_trend = data["trends"].get("trends", {}).get("Revenue", {})
            cagr = rev_trend.get("growth_rate")
            
            latest_npm = ratios.get("ProfitMargin", [None]*len(metrics["years"]))[latest_idx] if "ProfitMargin" in ratios else ratios.get("Profit Margin", [None]*len(metrics["years"]))[latest_idx]
            latest_de = ratios.get("Debt-to-Equity", [None]*len(metrics["years"]))[latest_idx]
            latest_cr = ratios.get("Current Ratio", [None]*len(metrics["years"]))[latest_idx]
            latest_rev = metrics.get("Revenue", [None]*len(metrics["years"]))[latest_idx]
            latest_net = metrics.get("Net Profit", [None]*len(metrics["years"]))[latest_idx]
            
            comp_records.append({
                "Company Name": name,
                "Recommendation": rec.get("recommendation", "Moderate Risk"),
                "Stock Strength": strength.get("score", 50),
                "Latest Revenue": f"₹{latest_rev:,.1f} Cr" if latest_rev is not None else "N/A",
                "Latest Net Profit": f"₹{latest_net:,.1f} Cr" if latest_net is not None else "N/A",
                "Revenue CAGR": f"{cagr:.1%}" if cagr is not None else "N/A",
                "Net Profit Margin": f"{latest_npm:.1%}" if latest_npm is not None else "N/A",
                "Debt-to-Equity": f"{latest_de:.2f}x" if latest_de is not None else "N/A",
                "Current Ratio": f"{latest_cr:.2f}x" if latest_cr is not None else "N/A",
            })
            
        comp_df = pd.DataFrame(comp_records)
        st.table(comp_df.set_index("Company Name"))
        
        # Charts for Comparison
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            # Bar chart comparing Stock Strength Scores
            fig_score = go.Figure(go.Bar(
                x=comp_df["Company Name"],
                y=comp_df["Stock Strength"],
                marker_color="#60a5fa",
                text=comp_df["Stock Strength"],
                textposition="auto"
            ))
            fig_score.update_layout(
                title="Stock Strength Index Comparison (out of 100)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", range=[0, 100]),
                xaxis=dict(showgrid=False),
                font=dict(color="rgba(255,255,255,0.7)"),
            )
            st.plotly_chart(fig_score, use_container_width=True)
            
        with col_c2:
            # Bar chart comparing Revenue Growth
            # Filter clean float values for plot
            cagr_vals = []
            for name, data in st.session_state.companies_data.items():
                rev_trend = data["trends"].get("trends", {}).get("Revenue", {})
                cagr_vals.append(rev_trend.get("growth_rate", 0) * 100) # percentage
                
            fig_growth = go.Figure(go.Bar(
                x=comp_df["Company Name"],
                y=cagr_vals,
                marker_color="#10b981",
                text=[f"{v:.1f}%" for v in cagr_vals],
                textposition="auto"
            ))
            fig_growth.update_layout(
                title="Revenue CAGR (%) Comparison",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
                xaxis=dict(showgrid=False),
                font=dict(color="rgba(255,255,255,0.7)"),
            )
            st.plotly_chart(fig_growth, use_container_width=True)
