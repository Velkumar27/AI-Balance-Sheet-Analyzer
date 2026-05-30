import os
import json
from typing import Dict, List, Any, Optional
from openai import OpenAI
from prompts.analysis_prompts import RECOMMENDATION_PROMPT, SYSTEM_ANALYST_PROMPT, FULL_ANALYSIS_PROMPT

class LLMAnalyzer:
    """
    Orchestrates LLM evaluation of corporate financial statements.
    Generates detailed qualitative reports and investment ratings using GPT-4o.
    """
    def __init__(self, api_key: Optional[str] = None, model_name: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.model_name = model_name or os.environ.get("OPENAI_MODEL", "gpt-4o")

    def _get_client(self) -> OpenAI:
        if not self.api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY must be provided or set in environment variables.")
            self.api_key = api_key
        return OpenAI(api_key=self.api_key)

    def analyze_company_statements(
        self,
        company_name: str,
        sheets_dict: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Generates a full text-based research analysis of the company's financial sheets.
        """
        client = self._get_client()
        
        # Focus on core sheets to prevent exceeding token limits on large workbooks
        important_sheets = ["balance", "p&l", "profit", "loss", "income", "cash flow", "ratio", "kpi"]
        filtered_sheets = {}
        for s_name, s_data in sheets_dict.items():
            if any(term in s_name.lower() for term in important_sheets) or len(sheets_dict) <= 6:
                filtered_sheets[s_name] = s_data
        if not filtered_sheets:
            filtered_sheets = sheets_dict
            
        context = ""
        for s_name, s_data in filtered_sheets.items():
            context += s_data["markdown"] + "\n\n"
            
        prompt = FULL_ANALYSIS_PROMPT.format(
            company_name=company_name,
            context=context
        )
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_ANALYST_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating financial research thesis: {str(e)}"

    def generate_recommendation_panel(
        self,
        company_name: str,
        sheets_dict: Dict[str, Dict[str, Any]],
        metrics_data: Dict[str, Any],
        ratios_data: Dict[str, List[Any]],
        trend_data: Dict[str, Any],
        strength_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generates structured recommendation: Safe Buy, Moderate Risk, or High Risk,
        along with reasoning, strengths, weaknesses, growth drivers, and risk factors.
        """
        client = self._get_client()
        
        # Build context
        context = ""
        # Focus on sheets that sound like core sheets to keep prompt size reasonable if huge
        important_sheets = ["balance", "p&l", "profit", "loss", "income", "cash flow", "ratio", "kpi"]
        for s_name, s_data in sheets_dict.items():
            if any(term in s_name.lower() for term in important_sheets) or len(sheets_dict) <= 6:
                context += s_data["markdown"] + "\n\n"
                
        # Format inputs for JSON injection
        ratios_json = json.dumps(ratios_data, indent=2)
        trends_json = json.dumps(trend_data.get("trends", {}), indent=2)
        risk_flags_str = ", ".join(strength_data.get("risk_flags", []))
        strength_score = strength_data.get("score", 50)
        
        prompt = RECOMMENDATION_PROMPT.format(
            company_name=company_name,
            ratios_json=ratios_json,
            strength_score=strength_score,
            trends_json=trends_json,
            risk_flags=risk_flags_str,
            context=context
        )
        
        # Fallback values in case LLM fails or is not JSON compliant
        fallback_recommendation = {
            "recommendation": "Moderate Risk",
            "reasoning": "Fallback analysis triggered. Please check input parameters or OpenAI API connection.",
            "strengths": ["Data parsed successfully", "Tabular structures intact"],
            "weaknesses": ["API call or parsing failed during final evaluation"],
            "growth_indicators": ["N/A"],
            "risk_analysis": ["Failed to calculate final recommendations with LLM. Using quantitative heuristics."],
            "confidence_score": 50,
            "investment_thesis": "The quantitative score was calculated, but LLM analysis failed. Please review the financial ratios and trend charts manually."
        }
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_ANALYST_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            raw_json = response.choices[0].message.content
            clean_json = raw_json.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
                
            data = json.loads(clean_json)
            
            # Basic schema checks
            required_keys = ["recommendation", "reasoning", "strengths", "weaknesses", "growth_indicators", "risk_analysis", "confidence_score", "investment_thesis"]
            for key in required_keys:
                if key not in data:
                    data[key] = fallback_recommendation[key]
                    
            # Normalize recommendation to expected values
            rec_str = str(data["recommendation"]).lower()
            if "strong buy" in rec_str:
                data["recommendation"] = "Strong Buy"
            elif "buy" in rec_str:
                data["recommendation"] = "Buy"
            elif "sell" in rec_str:
                data["recommendation"] = "Sell"
            elif "avoid" in rec_str:
                data["recommendation"] = "Avoid"
            else:
                data["recommendation"] = "Hold"
                
            return data
            
        except Exception as e:
            print(f"Error in LLM recommendation panel: {e}")
            # Dynamic adjust of recommendation based on Stock Strength Index heuristics
            if strength_score >= 80:
                fallback_recommendation["recommendation"] = "Strong Buy"
                fallback_recommendation["reasoning"] = f"Deterministic strength index is exceptionally high ({strength_score}/100), indicating institutional-grade strength."
            elif strength_score >= 65:
                fallback_recommendation["recommendation"] = "Buy"
                fallback_recommendation["reasoning"] = f"Deterministic strength index is healthy ({strength_score}/100), suggesting strong buy-side characteristics."
            elif strength_score >= 45:
                fallback_recommendation["recommendation"] = "Hold"
                fallback_recommendation["reasoning"] = f"Deterministic strength index is moderate ({strength_score}/100), suggesting balanced risks and fair value."
            elif strength_score >= 25:
                fallback_recommendation["recommendation"] = "Sell"
                fallback_recommendation["reasoning"] = f"Deterministic strength index is low ({strength_score}/100), highlighting fundamental headwinds."
            else:
                fallback_recommendation["recommendation"] = "Avoid"
                fallback_recommendation["reasoning"] = f"Deterministic strength index is critically low ({strength_score}/100), highlighting severe risk alerts."
            return fallback_recommendation
