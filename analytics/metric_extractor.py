import re
import json
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from openai import OpenAI
from prompts.analysis_prompts import KPI_EXTRACTION_PROMPT

class MetricExtractor:
    """
    Extracts core financial metrics from sheet DataFrames and markdown tables.
    Uses regex/keyword matching first, and falls back to LLM extraction if incomplete.
    """
    TARGET_METRICS = [
        "Revenue",
        "Net Profit",
        "EBITDA",
        "Total Debt",
        "Operating Cash Flow",
        "Free Cash Flow",
        "Total Equity",
        "Total Assets",
        "Total Liabilities",
        "Current Assets",
        "Current Liabilities",
        "Interest Expense",
        "Finance Costs",
        "Market Capitalization",
        "PE Ratio"
    ]
    
    def __init__(self, openai_client: Optional[OpenAI] = None, model_name: str = "gpt-4o"):
        self.openai_client = openai_client
        self.model_name = model_name

    def extract_metrics(self, sheets_dict: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main entrypoint. Extracts metrics over years across all sheets.
        Returns:
            {
                "years": [2021, 2022, 2023],
                "metrics": {
                    "Revenue": [val21, val22, val23],
                    ...
                },
                "currency": str,
                "extraction_method": "deterministic" | "hybrid_llm"
            }
        """
        # 1. Deterministic extraction from Pandas DataFrames
        det_data = self._extract_deterministic(sheets_dict)
        
        # Check if we got enough data
        has_years = len(det_data.get("years", [])) > 0
        missing_metrics = []
        for m in self.TARGET_METRICS:
            vals = det_data.get("metrics", {}).get(m, [])
            if not vals or all(v is None for v in vals):
                missing_metrics.append(m)
                
        # If we have years, but are missing critical metrics (like Revenue, Net Profit, Equity),
        # or if we couldn't find any years, let's fall back to LLM extraction
        if not has_years or len(missing_metrics) > 5:  # Slightly higher threshold since we added more metrics
            llm_data = self._extract_with_llm(sheets_dict)
            if llm_data and len(llm_data.get("years", [])) > 0:
                llm_data["extraction_method"] = "hybrid_llm"
                return llm_data
                
        det_data["extraction_method"] = "deterministic"
        return det_data

    def _extract_deterministic(self, sheets_dict: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extracts metrics using regex matching on DataFrame rows.
        """
        # Find years in all column headers
        years_set = set()
        year_cols_map = {} # maps sheet_name -> list of (year, col_name)
        
        year_pattern = re.compile(r"\b(20\d{2})\b")
        
        for s_name, s_data in sheets_dict.items():
            df = s_data["dataframe"]
            cols = df.columns
            sheet_years = []
            for col in cols:
                col_str = str(col)
                match = year_pattern.search(col_str)
                if match:
                    y = int(match.group(1))
                    sheet_years.append((y, col))
                    years_set.add(y)
            if sheet_years:
                # Sort by year ascending
                sheet_years.sort(key=lambda x: x[0])
                year_cols_map[s_name] = sheet_years
                
        sorted_years = sorted(list(years_set))
        
        # Initialize metrics dictionary
        metrics_out = {m: [None] * len(sorted_years) for m in self.TARGET_METRICS}
        
        # Helper to parse values
        def clean_val(val: Any) -> Optional[float]:
            if pd.isna(val):
                return None
            val_str = str(val).strip().replace(" ", "")
            if val_str.startswith('='):
                return None
            if not val_str or val_str in ["-", "—", "nil", "null", "N/A", "na"]:
                return 0.0
            
            is_neg = False
            if val_str.startswith('(') and val_str.endswith(')'):
                is_neg = True
                val_str = val_str[1:-1]
            elif val_str.startswith('-'):
                is_neg = True
                val_str = val_str[1:]
                
            val_str = re.sub(r"[^\d\.]", "", val_str)
            try:
                f_val = float(val_str)
                return -f_val if is_neg else f_val
            except ValueError:
                return None

        # Regex definitions for core metrics
        regex_map = {
            "Revenue": re.compile(r"^(?=.*(revenue|sales|turnover|topline|operating income|income from operations))(?!.*(cost|growth|other|non-operating|financial|asset|inventory|receivable|payable|ratio|turnover.*ratio)).*$", re.I),
            "Net Profit": re.compile(r"^(?=.*(net profit|net income|profit after tax|pat|profit for the year|earnings for the year|profit.*loss.*after tax))(?!.*(before|margin|percent|pre-tax)).*$", re.I),
            "EBITDA": re.compile(r"^(?=.*(ebitda|operating profit|ebit|earnings before interest.*tax|operating income))(?!.*(margin|percent|cost)).*$", re.I),
            "Total Debt": re.compile(r"^(?=.*(total debt|borrowings|long term debt|short term debt|total borrowings|long-term borrowings|short-term borrowings))(?!.*(equity|ratio|cost|service)).*$", re.I),
            "Operating Cash Flow": re.compile(r"^(?=.*(operating cash flow|cash flow.*operating|cash.*operating|cash from operations|operating activities))(?!.*(before|net decrease|net increase)).*$", re.I),
            "Free Cash Flow": re.compile(r"^(?=.*(free cash flow|fcf))(?!.*(yield|margin)).*$", re.I),
            "Total Equity": re.compile(r"^(?=.*(total equity|shareholder.*equity|shareholders' funds|equity share capital|total share capital|share capital))(?!.*(ratio|debt)).*$", re.I),
            "Total Assets": re.compile(r"^(?=.*(total assets|assets))(?!.*(turnover|ratio|current assets|non-current assets)).*$", re.I),
            "Total Liabilities": re.compile(r"^(?=.*(total liabilities|liabilities))(?!.*(current liabilities|non-current liabilities)).*$", re.I),
            "Current Assets": re.compile(r"^(?=.*(current assets))(?!.*(total assets|non-current)).*$", re.I),
            "Current Liabilities": re.compile(r"^(?=.*(current liabilities))(?!.*(total liabilities|non-current)).*$", re.I),
            "Interest Expense": re.compile(r"^(?=.*(interest expense|finance costs|interest paid))(?!.*(received|income)).*$", re.I),
            "Finance Costs": re.compile(r"^(?=.*(finance cost|finance expense))(?!.*(income|received)).*$", re.I),
            "Market Capitalization": re.compile(r"^(?=.*(market capitalization|market cap|market value of equity))(?!.*(ratio|growth)).*$", re.I),
            "PE Ratio": re.compile(r"^(?=.*(p/e ratio|pe ratio|price to earnings|price\/earnings ratio))(?!.*(growth|percent)).*$", re.I)
        }

        # Scan each sheet
        for s_name, s_data in sheets_dict.items():
            df = s_data["dataframe"]
            if df.empty or df.shape[1] < 2:
                continue
                
            first_col = df.columns[0]
            sheet_years = year_cols_map.get(s_name, [])
            if not sheet_years:
                continue
                
            # Iterate through rows
            for idx, row in df.iterrows():
                label = str(row[first_col]).strip()
                if not label or label == "nan":
                    continue
                    
                # Match against regexes
                for metric_name, pattern in regex_map.items():
                    if pattern.search(label):
                        # We found a row match. Let's fill the values for each year
                        for year, col_name in sheet_years:
                            val = clean_val(row[col_name])
                            if val is not None:
                                year_idx = sorted_years.index(year)
                                # If we already extracted a value, prefer a non-zero value or keep the first match
                                if metrics_out[metric_name][year_idx] is None or metrics_out[metric_name][year_idx] == 0:
                                    metrics_out[metric_name][year_idx] = val

        # Handle specific calculations if FCF is missing but we have Operating Cash Flow and Capex
        # Let's see if we can look for Capital Expenditures
        capex_pattern = re.compile(r"capex|capital expenditure|purchase of property|additions to property", re.I)
        capex_vals = [None] * len(sorted_years)
        
        for s_name, s_data in sheets_dict.items():
            df = s_data["dataframe"]
            if df.empty or df.shape[1] < 2:
                continue
            first_col = df.columns[0]
            sheet_years = year_cols_map.get(s_name, [])
            if not sheet_years:
                continue
            for idx, row in df.iterrows():
                label = str(row[first_col]).strip()
                if capex_pattern.search(label):
                    for year, col_name in sheet_years:
                        val = clean_val(row[col_name])
                        if val is not None:
                            year_idx = sorted_years.index(year)
                            # Capex is usually reported as negative in cash flows; take absolute value
                            capex_vals[year_idx] = abs(val)

        # Compute FCF = Operating Cash Flow - Capex if FCF is not found
        for y_idx in range(len(sorted_years)):
            if metrics_out["Free Cash Flow"][y_idx] is None:
                ocf = metrics_out["Operating Cash Flow"][y_idx]
                capex = capex_vals[y_idx]
                if ocf is not None:
                    if capex is not None:
                        metrics_out["Free Cash Flow"][y_idx] = ocf - capex
                    else:
                        metrics_out["Free Cash Flow"][y_idx] = ocf  # Fallback to OCF if Capex not found

        return {
            "years": sorted_years,
            "metrics": metrics_out,
            "currency": "INR (Crores)"
        }

    def _extract_with_llm(self, sheets_dict: Dict[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Falls back to GPT-4o to parse sheet data tables into the target JSON format.
        """
        if not self.openai_client:
            return None
            
        # Filter to core sheets (Balance Sheet, Income Statement, Cash Flow) to avoid token rate limits
        core_keywords = [
            "income", "profit", "loss", "p&l", "p and l", "p & l", "revenue",
            "balance", "asset", "liabilit", "equity", "shareholder",
            "cash flow", "cashflow", "cf", "operating activities"
        ]
        exclude_keywords = ["note", "disclosure", "index", "readme", "definition", "chart", "graph", "calculation", "formula"]
        
        filtered_sheets = {}
        for s_name, s_data in sheets_dict.items():
            name_lower = s_name.lower()
            has_core = any(kw in name_lower for kw in core_keywords)
            has_exclude = any(kw in name_lower for kw in exclude_keywords)
            if has_core and not has_exclude:
                filtered_sheets[s_name] = s_data
                
        if not filtered_sheets:
            filtered_sheets = sheets_dict
            
        # Combine filtered sheet markdown tables
        combined_markdown = ""
        for s_name, s_data in filtered_sheets.items():
            combined_markdown += s_data["markdown"] + "\n\n"
            
        prompt = KPI_EXTRACTION_PROMPT.format(sheet_content=combined_markdown)
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a financial data parser. Extract and return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            
            raw_json = response.choices[0].message.content
            # Clean up potential markdown wrapper
            clean_json = raw_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
                
            data = json.loads(clean_json)
            
            # Standardize output keys
            if "years" in data and "metrics" in data:
                # Ensure all target metrics exist in metrics dict
                metrics = data["metrics"]
                standard_metrics = {}
                for m in self.TARGET_METRICS:
                    standard_metrics[m] = metrics.get(m, [None] * len(data["years"]))
                data["metrics"] = standard_metrics
                return data
        except Exception as e:
            print(f"Error in LLM KPI extraction: {e}")
            
        return None
