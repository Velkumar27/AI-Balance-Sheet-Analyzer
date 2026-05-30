from typing import Dict, List, Any, Optional, Tuple

class RiskScorer:
    """
    Calculates a proprietary Stock Strength Index (0 to 100) based on financial health,
    profitability, cash flows, growth, stability, and flags specific risk indicators.
    Weighted categories:
      1. Growth: 25%
      2. Profitability: 20%
      3. Cash Flow: 20%
      4. Debt: 15%
      5. Valuation: 10%
      6. Capital Allocation: 10%
    """
    
    @staticmethod
    def calculate_strength_score(
        metrics_data: Dict[str, Any],
        ratios_data: Dict[str, List[Any]],
        trend_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Computes the weighted 6-category Stock Strength Index score, breakdown, and flags risk items.
        """
        years = metrics_data.get("years", [])
        metrics = metrics_data.get("metrics", {})
        anomalies = trend_data.get("anomalies", [])
        n_years = len(years)
        
        score_breakdown = {
            "Growth": 0.0,
            "Profitability": 0.0,
            "Cash Flow": 0.0,
            "Debt": 0.0,
            "Valuation": 0.0,
            "Capital Allocation": 0.0
        }
        
        risk_flags = []
        missing_diagnostics = []
        
        if n_years == 0:
            return {
                "score": 0,
                "breakdown": {k: 0 for k in score_breakdown.keys()},
                "risk_flags": ["No data available for analysis."],
                "missing_data_diagnostics": ["All core metrics missing."],
                "rating": "Avoid"
            }
            
        # Target years for evaluation (focus window: 2024 to 2026)
        latest_idx = -1
        prev_idx = -2 if n_years > 1 else -1
        prev_2_idx = -3 if n_years > 2 else prev_idx
        
        latest_year = years[latest_idx]
        
        # Helper to retrieve metric safely
        def get_m(name: str, idx: int) -> Optional[float]:
            vals = metrics.get(name, [])
            if vals and abs(idx) <= len(vals) and vals[idx] is not None:
                try:
                    return float(vals[idx])
                except ValueError:
                    return None
            return None

        # Helper to retrieve ratio safely
        def get_r(name: str, idx: int) -> Optional[float]:
            vals = ratios_data.get(name, [])
            if not vals:
                # Try with alternate names
                alt_name = name.replace("Margin", " Margin").replace("-to-", "-to-")
                vals = ratios_data.get(alt_name, [])
            if vals and abs(idx) <= len(vals) and vals[idx] is not None:
                try:
                    return float(vals[idx])
                except ValueError:
                    return None
            return None

        # ----------------------------------------------------
        # 1. Growth (Max 25 pts)
        # ----------------------------------------------------
        growth_score = 0.0
        
        # A. Revenue CAGR (focus 2024-2026 or last 3 years)
        rev_latest = get_m("Revenue", latest_idx)
        rev_prev = get_m("Revenue", prev_2_idx)
        rev_cagr = None
        
        if rev_latest and rev_prev and rev_prev > 0:
            gap = years[latest_idx] - years[prev_2_idx]
            if gap > 0:
                rev_cagr = (rev_latest / rev_prev) ** (1 / gap) - 1
                
        if rev_cagr is None:
            # Fallback to trend CAGR if available
            rev_cagr = trend_data.get("trends", {}).get("Revenue", {}).get("growth_rate")
            
        if rev_cagr is not None:
            if rev_cagr >= 0.15:
                growth_score += 10.0
            elif rev_cagr >= 0.08:
                growth_score += 7.0
            elif rev_cagr >= 0.03:
                growth_score += 4.0
            elif rev_cagr >= 0.0:
                growth_score += 2.0
            else:
                growth_score += 0.0
                risk_flags.append(f"Topline revenue contraction: CAGR is negative ({rev_cagr:.1%}) over the focus period.")
        else:
            missing_diagnostics.append("Revenue CAGR")
            
        # B. Net Profit CAGR (focus 2024-2026 or last 3 years)
        pat_latest = get_m("Net Profit", latest_idx)
        pat_prev = get_m("Net Profit", prev_2_idx)
        pat_cagr = None
        
        if pat_latest and pat_prev and pat_prev > 0 and pat_latest > 0:
            gap = years[latest_idx] - years[prev_2_idx]
            if gap > 0:
                pat_cagr = (pat_latest / pat_prev) ** (1 / gap) - 1
                
        if pat_cagr is None:
            pat_cagr = trend_data.get("trends", {}).get("Net Profit", {}).get("growth_rate")
            
        if pat_cagr is not None:
            if pat_cagr >= 0.15:
                growth_score += 10.0
            elif pat_cagr >= 0.08:
                growth_score += 7.0
            elif pat_cagr >= 0.03:
                growth_score += 4.0
            elif pat_cagr >= 0.0:
                growth_score += 2.0
            else:
                growth_score += 0.0
                risk_flags.append(f"Earnings contraction: Net Profit CAGR is negative ({pat_cagr:.1%}) over the focus period.")
        else:
            missing_diagnostics.append("Net Profit CAGR")
            
        # C. Free Cash Flow Growth / Trend (focus 2024-2026)
        fcf_latest = get_m("Free Cash Flow", latest_idx)
        fcf_prev = get_m("Free Cash Flow", prev_idx)
        
        if fcf_latest is not None:
            if fcf_latest > 0:
                if fcf_prev is not None and fcf_latest >= fcf_prev:
                    growth_score += 5.0
                else:
                    growth_score += 3.0
            else:
                growth_score += 0.0
        else:
            missing_diagnostics.append("Free Cash Flow Growth")
            
        score_breakdown["Growth"] = min(25.0, growth_score)
        
        # ----------------------------------------------------
        # 2. Profitability (Max 20 pts)
        # ----------------------------------------------------
        profitability_score = 0.0
        
        # A. Net Profit Margin (latest year)
        latest_npm = get_r("Profit Margin", latest_idx)
        if latest_npm is not None:
            if latest_npm >= 0.15:
                profitability_score += 8.0
            elif latest_npm >= 0.08:
                profitability_score += 5.0
            elif latest_npm >= 0.02:
                profitability_score += 2.0
            else:
                profitability_score += 0.0
                if latest_npm < 0:
                    risk_flags.append(f"Net Profit Margin is negative in the latest year ({latest_npm:.1%}).")
        else:
            missing_diagnostics.append("Net Profit Margin")
            
        # B. EBITDA Margin (latest year)
        latest_ebitda_m = get_r("EBITDA Margin", latest_idx)
        if latest_ebitda_m is not None:
            if latest_ebitda_m >= 0.20:
                profitability_score += 7.0
            elif latest_ebitda_m >= 0.12:
                profitability_score += 4.0
            elif latest_ebitda_m >= 0.05:
                profitability_score += 2.0
            else:
                profitability_score += 0.0
        else:
            missing_diagnostics.append("EBITDA Margin")
            
        # C. Margin YoY Trend (2024-2026)
        prev_npm = get_r("Profit Margin", prev_idx)
        if latest_npm is not None and prev_npm is not None:
            margin_diff = latest_npm - prev_npm
            if margin_diff >= 0:
                profitability_score += 5.0
            else:
                profitability_score += 1.0
                if margin_diff < -0.02:
                    risk_flags.append(f"Margin compression: Net profit margins declined by {abs(margin_diff):.1%} YoY.")
        else:
            profitability_score += 3.0 # Neutral fallback
            
        score_breakdown["Profitability"] = min(20.0, profitability_score)
        
        # ----------------------------------------------------
        # 3. Cash Flow (Max 20 pts)
        # ----------------------------------------------------
        cash_flow_score = 0.0
        
        # A. OCF vs Net Profit (Earnings Quality)
        latest_ocf = get_m("Operating Cash Flow", latest_idx)
        latest_pat = get_m("Net Profit", latest_idx)
        
        if latest_ocf is not None and latest_pat is not None:
            if latest_ocf >= latest_pat:
                cash_flow_score += 10.0
            elif latest_ocf >= 0.7 * latest_pat:
                cash_flow_score += 7.0
            elif latest_ocf > 0:
                cash_flow_score += 4.0
            else:
                cash_flow_score += 0.0
                risk_flags.append(f"Negative operating cash flow: Operations are consuming cash ({latest_ocf:,.2f} Cr).")
        else:
            missing_diagnostics.append("OCF vs Net Profit")
            
        # B. Free Cash Flow Positivity (latest year)
        if fcf_latest is not None:
            if fcf_latest > 0:
                cash_flow_score += 5.0
            elif fcf_latest == 0:
                cash_flow_score += 2.0
            else:
                cash_flow_score += 0.0
                risk_flags.append(f"Negative Free Cash Flow: Capital expenditures exceed cash generated from operations.")
        else:
            missing_diagnostics.append("FCF Positivity")
            
        # C. Cash Flow Conversion (Avg OCF / Net Profit over last 3 years)
        ocf_vals = [get_m("Operating Cash Flow", i) for i in [latest_idx, prev_idx, prev_2_idx]]
        pat_vals = [get_m("Net Profit", i) for i in [latest_idx, prev_idx, prev_2_idx]]
        
        ocf_clean = [o for o in ocf_vals if o is not None]
        pat_clean = [p for p in pat_vals if p is not None]
        
        if len(ocf_clean) >= 2 and len(pat_clean) >= 2 and sum(pat_clean) > 0:
            avg_conversion = sum(ocf_clean) / sum(pat_clean)
            if avg_conversion >= 0.90:
                cash_flow_score += 5.0
            elif avg_conversion >= 0.50:
                cash_flow_score += 3.0
            else:
                cash_flow_score += 0.0
                risk_flags.append(f"Low cash conversion: Average OCF/Net Profit conversion is poor ({avg_conversion:.1%}).")
        else:
            cash_flow_score += 3.0
            
        score_breakdown["Cash Flow"] = min(20.0, cash_flow_score)
        
        # ----------------------------------------------------
        # 4. Debt (Max 15 pts)
        # ----------------------------------------------------
        debt_score = 0.0
        
        # A. Debt-to-Equity
        latest_de = get_r("Debt-to-Equity", latest_idx)
        if latest_de is not None:
            if latest_de <= 0.3:
                debt_score += 7.0
            elif latest_de <= 0.8:
                debt_score += 5.0
            elif latest_de <= 1.5:
                debt_score += 3.0
            else:
                debt_score += 0.0
                risk_flags.append(f"Highly leveraged balance sheet: Debt-to-Equity is elevated at {latest_de:.2f}x.")
        else:
            latest_debt = get_m("Total Debt", latest_idx)
            if latest_debt == 0 or latest_debt is None:
                debt_score += 7.0 # No debt is ideal
            else:
                missing_diagnostics.append("Debt-to-Equity")
                
        # B. Interest Coverage
        latest_int_cov = get_r("Interest Coverage", latest_idx)
        if latest_int_cov is not None:
            if latest_int_cov >= 5.0:
                debt_score += 5.0
            elif latest_int_cov >= 2.0:
                debt_score += 3.0
            else:
                debt_score += 0.0
                risk_flags.append(f"Weak solvency cover: Interest Coverage ratio is low at {latest_int_cov:.2f}x.")
        else:
            missing_diagnostics.append("Interest Coverage")
            
        # C. Net Debt position
        latest_cash = get_m("Cash & Bank", latest_idx) or get_m("Cash and Cash Equivalents", latest_idx) or 0.0
        latest_debt_val = get_m("Total Debt", latest_idx) or 0.0
        
        if latest_cash >= latest_debt_val:
            debt_score += 3.0 # Net cash positive!
        else:
            debt_score += 1.0
            
        score_breakdown["Debt"] = min(15.0, debt_score)
        
        # ----------------------------------------------------
        # 5. Valuation (Max 10 pts)
        # ----------------------------------------------------
        valuation_score = 0.0
        pe_val = get_m("PE Ratio", latest_idx)
        
        # If PE is not explicitly extracted, calculate if Market Cap is available
        if pe_val is None:
            mcap = get_m("Market Capitalization", latest_idx)
            pat = get_m("Net Profit", latest_idx)
            if mcap and pat and pat > 0:
                pe_val = mcap / pat
                
        if pe_val is not None:
            if pe_val <= 15.0:
                valuation_score += 10.0
            elif pe_val <= 25.0:
                valuation_score += 7.0
            elif pe_val <= 45.0:
                valuation_score += 4.0
            else:
                valuation_score += 1.0
                if pe_val > 60:
                    risk_flags.append(f"Highly priced: Trailing P/E ratio is high ({pe_val:.1f}x).")
        else:
            # Fallback valuation proxy using ROE and growth points
            latest_roe = get_r("ROE", latest_idx)
            if latest_roe is not None:
                if latest_roe >= 0.15 and growth_score >= 15.0:
                    valuation_score += 8.0
                elif latest_roe >= 0.10:
                    valuation_score += 6.0
                else:
                    valuation_score += 4.0
            else:
                valuation_score += 5.0 # Neutral fallback
                missing_diagnostics.append("Valuation Ratio (PE)")
                
        score_breakdown["Valuation"] = min(10.0, valuation_score)
        
        # ----------------------------------------------------
        # 6. Capital Allocation (Max 10 pts)
        # ----------------------------------------------------
        allocation_score = 0.0
        
        # A. ROE
        latest_roe = get_r("ROE", latest_idx)
        if latest_roe is not None:
            if latest_roe >= 0.20:
                allocation_score += 4.0
            elif latest_roe >= 0.12:
                allocation_score += 2.0
            elif latest_roe >= 0.05:
                allocation_score += 1.0
            else:
                allocation_score += 0.0
                risk_flags.append(f"Sub-par capital returns: Return on Equity is low ({latest_roe:.1%}).")
        else:
            missing_diagnostics.append("ROE")
            
        # B. ROA
        latest_roa = get_r("ROA", latest_idx)
        if latest_roa is not None:
            if latest_roa >= 0.10:
                allocation_score += 2.0
            elif latest_roa >= 0.05:
                allocation_score += 1.0
        else:
            missing_diagnostics.append("ROA")
            
        # C. Dividend Payout Ratio
        div_amt = get_m("Dividend Amount", latest_idx)
        pat = get_m("Net Profit", latest_idx)
        div_payout = None
        if div_amt is not None and pat and pat > 0:
            div_payout = div_amt / pat
            
        if div_payout is not None:
            if 0.20 <= div_payout <= 0.80:
                allocation_score += 2.0 # Healthy cash payout to shareholders
            elif div_payout > 0:
                allocation_score += 1.0
            else:
                if latest_roe is not None and latest_roe >= 0.15:
                    allocation_score += 1.0 # Fine not to pay dividend if reinvesting at high ROE
        else:
            if latest_roe is not None and latest_roe >= 0.15:
                allocation_score += 1.0
                
        # D. Asset Turnover
        latest_rev_val = get_m("Revenue", latest_idx)
        latest_assets = get_m("Total Assets", latest_idx)
        if latest_rev_val and latest_assets and latest_assets > 0:
            asset_turnover = latest_rev_val / latest_assets
            if asset_turnover >= 1.2:
                allocation_score += 2.0
            elif asset_turnover >= 0.6:
                allocation_score += 1.0
        else:
            allocation_score += 1.0
            
        score_breakdown["Capital Allocation"] = min(10.0, allocation_score)
        
        # ----------------------------------------------------
        # Scoring Aggregation & Penalties
        # ----------------------------------------------------
        raw_score = sum(score_breakdown.values())
        
        # Deduct penalties for severe missing data or anomalies
        missing_count = len([d for d in missing_diagnostics if "Growth" not in d])
        penalty_missing = missing_count * 3
        
        high_severity_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        penalty_anomalies = len(high_severity_anomalies) * 6
        
        # Severe penalty for negative operating cash flow
        penalty_ocf = 0
        if latest_ocf is not None and latest_ocf < 0:
            penalty_ocf = 8
            
        final_score = raw_score - penalty_missing - penalty_anomalies - penalty_ocf
        final_score = max(0, min(100, int(round(final_score))))
        
        # Rating assignment
        rating = RiskScorer.get_rating(final_score)
        
        # Append anomaly warnings to risk flags
        for a in anomalies:
            risk_flags.append(a["message"])
            
        if penalty_missing > 0:
            risk_flags.append(f"Penalized score by {penalty_missing} pts due to missing indicators: {', '.join(missing_diagnostics)}")
            
        return {
            "score": final_score,
            "breakdown": score_breakdown,
            "risk_flags": list(set(risk_flags)),  # Deduplicate
            "missing_data_diagnostics": missing_diagnostics,
            "rating": rating
        }
        
    @staticmethod
    def get_rating(score: int) -> str:
        """
        Maps numerical stock strength index score to 5-tier recommendation.
        """
        if score >= 80:
            return "Strong Buy"
        elif score >= 65:
            return "Buy"
        elif score >= 45:
            return "Hold"
        elif score >= 25:
            return "Sell"
        else:
            return "Avoid"
