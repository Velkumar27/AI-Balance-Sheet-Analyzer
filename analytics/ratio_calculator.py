from typing import Dict, List, Any, Optional

class RatioCalculator:
    """
    Computes key financial ratios from raw metrics dictionary.
    Handles division by zero and missing values gracefully.
    """
    @staticmethod
    def calculate_ratios(metrics_data: Dict[str, Any]) -> Dict[str, List[Optional[float]]]:
        """
        Computes ratios over years.
        Args:
            metrics_data: Dict containing 'years' and 'metrics'
        Returns:
            Dict mapping ratio names to lists of values
        """
        years = metrics_data.get("years", [])
        metrics = metrics_data.get("metrics", {})
        n_years = len(years)
        
        ratios = {
            "Profit Margin": [None] * n_years,
            "Debt-to-Equity": [None] * n_years,
            "Current Ratio": [None] * n_years,
            "ROE": [None] * n_years,
            "ROA": [None] * n_years,
            "EBITDA Margin": [None] * n_years,
            "Free Cash Flow Margin": [None] * n_years,
            "Interest Coverage": [None] * n_years
        }
        
        for idx in range(n_years):
            rev = RatioCalculator._get_val(metrics, "Revenue", idx)
            net_prof = RatioCalculator._get_val(metrics, "Net Profit", idx)
            ebitda = RatioCalculator._get_val(metrics, "EBITDA", idx)
            debt = RatioCalculator._get_val(metrics, "Total Debt", idx)
            equity = RatioCalculator._get_val(metrics, "Total Equity", idx)
            assets = RatioCalculator._get_val(metrics, "Total Assets", idx)
            liabilities = RatioCalculator._get_val(metrics, "Total Liabilities", idx)
            fcf = RatioCalculator._get_val(metrics, "Free Cash Flow", idx)
            
            # 1. Profit Margin = Net Profit / Revenue
            if rev and net_prof is not None:
                ratios["Profit Margin"][idx] = net_prof / rev
                
            # 2. Debt-to-Equity = Total Debt / Total Equity
            if equity and debt is not None:
                ratios["Debt-to-Equity"][idx] = debt / equity
                
            # 3. Current Ratio = Current Assets / Current Liabilities
            # As a proxy if Current Assets/Liabilities are not separately extracted, we look for them.
            # Let's check if the metrics dict has "Current Assets" and "Current Liabilities".
            curr_assets = RatioCalculator._get_val(metrics, "Current Assets", idx)
            curr_liab = RatioCalculator._get_val(metrics, "Current Liabilities", idx)
            
            if curr_assets is not None and curr_liab:
                ratios["Current Ratio"][idx] = curr_assets / curr_liab
            elif assets is not None and liabilities:
                # Fallback to Total Assets / Total Liabilities if current assets/liabs are not present
                ratios["Current Ratio"][idx] = assets / liabilities
                
            # 4. ROE = Net Profit / Total Equity
            if equity and net_prof is not None:
                ratios["ROE"][idx] = net_prof / equity
                
            # 5. ROA = Net Profit / Total Assets
            if assets and net_prof is not None:
                ratios["ROA"][idx] = net_prof / assets
                
            # 6. EBITDA Margin = EBITDA / Revenue
            if rev and ebitda is not None:
                ratios["EBITDA Margin"][idx] = ebitda / rev
                
            # 7. Free Cash Flow Margin = Free Cash Flow / Revenue
            if rev and fcf is not None:
                ratios["Free Cash Flow Margin"][idx] = fcf / rev
                
            # 8. Interest Coverage = EBITDA / Interest Expense (or approximate using EBITDA / Debt * 0.07 if interest is missing)
            interest = RatioCalculator._get_val(metrics, "Interest Expense", idx) or RatioCalculator._get_val(metrics, "Finance Costs", idx)
            if ebitda is not None:
                if interest:
                    ratios["Interest Coverage"][idx] = ebitda / interest
                elif debt and debt > 0:
                    # Synthetic interest expense at 7% as a fallback proxy
                    synthetic_interest = debt * 0.07
                    ratios["Interest Coverage"][idx] = ebitda / synthetic_interest
                else:
                    # High interest coverage if no debt
                    ratios["Interest Coverage"][idx] = 100.0 if ebitda > 0 else 0.0
                    
        return ratios

    @staticmethod
    def _get_val(metrics: Dict[str, List[Any]], name: str, idx: int) -> Optional[float]:
        vals = metrics.get(name)
        if vals and idx < len(vals) and vals[idx] is not None:
            try:
                return float(vals[idx])
            except ValueError:
                return None
        return None
