# AI Financial Statement Analyzer (Streamlit + FAISS + GPT-4o RAG)

A production-grade fundamental financial analysis dashboard designed to read multi-sheet Excel workbooks, parse them into markdown grids, and run a Parent-Child retrieval augmented generation (RAG) pipeline to perform quantitative and qualitative equity research.

---

## Architecture Overview

```
[ User Uploads Excel File ]
            │
            ▼
 1. INGESTION & PARSING (Pandas & Openpyxl)
    - Clean outer empty cells & format floats
    - Convert sheets to aligned Markdown tables
            │
            ▼
 2. CHUNKING & STRUCTURING (Parent-Child Strategy)
    - Parent: Full sheet markdown tables
    - Child: 3-5 row slices containing column header rows (150-250 tokens)
            │
            ▼
 3. STORAGE & INDEXING
    - Embed child chunks using text-embedding-3-large
    - Store child vectors in FAISS index
    - Cache full parent markdown tables in memory / disk
            │
            ▼
 4. RETRIEVAL & RETRIEVER SWAP
    - Query embedded -> Search FAISS for top K child matches
    - Extract parent_id -> Swap child snippet for FULL parent sheet
            │
            ▼
 5. SYNTHESIS & REPORT GENERATION
    - LLM (GPT-4o) evaluates full sheet tables (unbroken relationships)
    - Deterministic extraction: Ratios, Stock Strength Index (0-100), Anomalies
    - Final recommendation: Safe Buy, Moderate Risk, High Risk
```

---

## Features

1. **Intelligent Spreadsheet Parsing**: Translates complex, multi-tab Excel files (`.xlsx`) containing Balance Sheets, Profit & Loss Statements, and Cash Flows into clean, markdown representation preserving row-column alignment.
2. **Deterministic & LLM Extraction**: Combines pattern-matching regexes with GPT-based schema parsers to extract key statement values.
3. **Proprietary Stock Strength Index (0-100)**: Evaluates solvency, profitability, growth rates, cash flow conversion, leverage, and applies automated penalties for anomalies or missing disclosures.
4. **Conversational Financial Q&A**: Uses the parent-child retriever to feed complete tables to GPT-4o, ensuring questions are answered with precise grounding and citations of source sheets.
5. **Interactive Data Charts**: Draws trend lines, radar breakdown graphs of the stock strength index, and waterfall generation bridges.
6. **Multi-Company Side-by-Side Comparison**: Compares the metrics, ratios, and final rating flags for multiple entities uploaded simultaneously.
7. **Report PDF Export**: Instantly compiles a publication-ready PDF brief using `reportlab`.

---

## Project Structure

```
├── ingestion/
│   ├── excel_parser.py      # Parses XLSX sheets and outputs cleaned markdowns
│   └── chunker.py           # Divides tables into row-level child segments
├── embeddings/
│   └── embedder.py          # OpenAI text-embedding-3-large client wrapper
├── retrieval/
│   ├── faiss_store.py       # FAISS index and local metadata pickle manager
│   └── parent_child_retriever.py # Coordinates index matching and parent sheet swap
├── analytics/
│   ├── metric_extractor.py  # Regex & LLM-fallback financial item parser
│   ├── ratio_calculator.py  # Computes key indicators (ROE, ROA, Debt-Equity, etc.)
│   ├── trend_analyzer.py    # Tracks growth rates, CAGRs, and financial anomalies
│   ├── risk_scorer.py       # Computes Stock Strength score (0-100) and penalties
│   └── llm_analyzer.py      # Connects GPT-4o for final recommendation and thesis
├── prompts/
│   ├── analysis_prompts.py  # Prompts for KPI extraction and final rating
│   └── chat_prompts.py      # Prompts for grounding conversational RAG
├── ui/
│   ├── styles.py            # Custom CSS styles (glassmorphism & glowing badges)
│   ├── components.py        # React-like component rendering (badges, KPI grids)
│   └── charts.py            # Plotly line, radar, and waterfall charts
├── app.py                   # Main Streamlit dashboard application
├── requirements.txt         # Package dependencies
└── .env.example             # Template for API keys
```

---

## Setup & Running Instructions

### 1. Installation
Install the required packages in your environment:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your OpenAI API Key:
```bash
cp .env.example .env
```
Open `.env` and edit:
```ini
OPENAI_API_KEY=sk-proj-...
```

### 3. Run the Streamlit Dashboard
Launch the local server:
```bash
streamlit run app.py
```

### 4. Downloading Financial Data
To analyze real companies, download their Excel balance sheet and financial statements from [Screener.in](https://www.screener.in/).
1. Go to Screener.in and search for a company.
2. Click on the "Export to Excel" button to download the workbook.
3. Upload the downloaded `.xlsx` file directly into the application via the sidebar to begin the fundamental analysis!

### 5. Interactive Testing (Demo Mode)
If you don't have Excel spreadsheets handy, open the dashboard in your browser and click the **💡 Load Demo Unilever Mock Data** button in the sidebar to populate the system with pre-formatted multi-sheet data (Balance Sheet, Income Statement, Cash Flow) and evaluate the features immediately!
