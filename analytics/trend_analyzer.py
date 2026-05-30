from typing import Dict, List, Any, Tuple, Optional
import numpy as np

class TrendAnalyzer:
    """
    Analyzes historical trends for key metrics, detects growth direction,
    calculates compound growth rates, and identifies financial anomalies.
    """
    @staticmethod
    def analyze_trends(metrics_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Runs trend and anomaly detection on the metrics.
        Returns:
            {
                "trends": {
                    "Revenue": {"earliest": X, "latest": Y, "growth_rate": G, "direction": D},
                    ...
                },
                "anomalies": [
                    {"type": "divergence", "message": "...", "severity": "high/medium"}
                ]
            }
        """
        years = metrics_data.get("years", [])
        metrics = metrics_data.get("metrics", {})
        n_years = len(years)
        
        results = {
            "trends": {},
            "anomalies": []
        }
        
        if n_years < 2:
            # Not enough data for trends
            return results
            
        target_metrics = ["Revenue", "Net Profit", "EBITDA", "Total Debt", "Operating Cash Flow", "Free Cash Flow"]
        
        for m in target_metrics:
            vals = metrics.get(m, [])
            # Filter non-nulls and align with years
            valid_pairs = [(y, v) for y, v in zip(years, vals) if v is not None]
            
            if len(valid_pairs) < 2:
                continue
                
            earliest_y, earliest_v = valid_pairs[0]
            latest_y, latest_v = valid_pairs[-1]
            
            # Calculate CAGR or simple growth rate
            gap = latest_y - earliest_y
            growth_rate = None
            
            if gap > 0 and earliest_v and earliest_v > 0 and latest_v and latest_v > 0:
                try:
                    growth_rate = (latest_v / earliest_v) ** (1 / gap) - 1
                except Exception:
                    pass
            elif earliest_v is not None and latest_v is not None:
                # Fallback to simple percentage change
                if earliest_v != 0:
                    growth_rate = (latest_v - earliest_v) / abs(earliest_v)
            
            # Determine direction
            direction = "stable"
            if growth_rate is not None:
                if growth_rate > 0.05:
                    direction = "growing"
                elif growth_rate < -0.05:
                    direction = "declining"
                    
            # Check for fluctuations
            changes = []
            for idx in range(len(valid_pairs) - 1):
                v1 = valid_pairs[idx][1]
                v2 = valid_pairs[idx+1][1]
                if v1 != 0 and v1 is not None and v2 is not None:
                    changes.append((v2 - v1) / abs(v1))
            
            # If changes alternate sign, label fluctuating
            if len(changes) >= 2:
                signs = [np.sign(c) for c in changes if c != 0]
                if len(signs) >= 2 and any(signs[i] != signs[i-1] for i in range(1, len(signs))):
                    direction = "fluctuating"
                    
            results["trends"][m] = {
                "earliest_year": earliest_y,
                "earliest_val": earliest_v,
                "latest_year": latest_y,
                "latest_val": latest_v,
                "growth_rate": growth_rate,
                "direction": direction
            }
            
            # Anomaly: Sudden YoY Drop or Spike
            for idx in range(len(valid_pairs) - 1):
                y1, v1 = valid_pairs[idx]
                y2, v2 = valid_pairs[idx+1]
                if v1 and v1 != 0:
                    change = (v2 - v1) / abs(v1)
                    if change < -0.3:
                        results["anomalies"].append({
                            "metric": m,
                            "year": y2,
                            "type": "sudden_drop",
                            "severity": "high" if m in ["Revenue", "Net Profit", "Operating Cash Flow"] else "medium",
                            "message": f"{m} dropped by {change:.1%} in {y2} (from {v1} to {v2})"
                        })
                    elif change > 0.6 and m == "Total Debt":
                        results["anomalies"].append({
                            "metric": m,
                            "year": y2,
                            "type": "debt_surge",
                            "severity": "high",
                            "message": f"Debt surged by {change:.1%} in {y2} (from {v1} to {v2})"
                        })
                        
        # Anomaly: Revenue vs Net Profit divergence
        # Revenue is growing, but Net Profit is declining
        rev_trend = results["trends"].get("Revenue")
        prof_trend = results["trends"].get("Net Profit")
        if rev_trend and prof_trend:
            if rev_trend["direction"] == "growing" and prof_trend["direction"] == "declining":
                results["anomalies"].append({
                    "metric": "Revenue/Net Profit",
                    "type": "margin_squeeze_divergence",
                    "severity": "high",
                    "message": "Divergence: Revenue is growing, but Net Profit is declining. This indicates a severe squeeze on margins."
                })
                
        # Anomaly: Earnings vs Operating Cash Flow divergence (High accruals / poor earnings quality)
        for idx in range(n_years):
            y = years[idx]
            net_prof = metrics.get("Net Profit", [None]*n_years)[idx]
            ocf = metrics.get("Operating Cash Flow", [None]*n_years)[idx]
            
            if net_prof is not None and ocf is not None:
                if net_prof > 0 and ocf < 0:
                    results["anomalies"].append({
                        "metric": "Cash Flow/Earnings",
                        "year": y,
                        "type": "unbacked_earnings",
                        "severity": "high",
                        "message": f"In {y}, Net Profit is positive ({net_prof}) but Operating Cash Flow is negative ({ocf}). Earnings are not backed by cash."
                    })
                elif ocf is not None and net_prof is not None and ocf < (net_prof * 0.5) and net_prof > 0:
                    results["anomalies"].append({
                        "metric": "Cash Flow/Earnings",
                        "year": y,
                        "type": "low_cash_conversion",
                        "severity": "medium",
                        "message": f"In {y}, Operating Cash Flow ({ocf}) is less than 50% of Net Profit ({net_prof}). This suggests potential working capital blockages."
                    })
                    
        return results
