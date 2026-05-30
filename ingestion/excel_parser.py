import pandas as pd
import openpyxl
from typing import Dict, List, Tuple, Any
import io
import re

class ExcelParser:
    """
    Parses multi-sheet Excel workbooks, cleans them, preserves structure,
    and converts them into markdown tables and clean Pandas DataFrames.
    """
    @staticmethod
    def parse_workbook(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Parses an Excel workbook from bytes, resolving all formulas dynamically
        to ensure no empty values are returned for uncalculated sheets.
        """
        workbook_name = filename.split('.')[0] if '.' in filename else filename
        
        # Load workbook with openpyxl (keep formulas to resolve them ourselves)
        try:
            wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False)
            sheet_names = wb.sheetnames
            
            # Load raw grid data for all sheets
            wb_data = {}
            for sheet_name in sheet_names:
                ws = wb[sheet_name]
                sheet_grid = []
                for r in range(1, ws.max_row + 1):
                    row_vals = []
                    for c in range(1, ws.max_column + 1):
                        row_vals.append(ws.cell(r, c).value)
                    sheet_grid.append(row_vals)
                wb_data[sheet_name] = sheet_grid
                
            # Resolve all cell formulas recursively
            resolved_cache = {}
            resolved_wb = {}
            for sheet_name in sheet_names:
                grid = wb_data[sheet_name]
                resolved_grid = []
                for r in range(len(grid)):
                    row_vals = []
                    for c in range(len(grid[r])):
                        row_vals.append(ExcelParser._resolve_cell(sheet_name, r, c, wb_data, resolved_cache))
                    resolved_grid.append(row_vals)
                resolved_wb[sheet_name] = resolved_grid
        except Exception as e:
            print(f"Error resolving formulas in workbook {filename}: {e}")
            resolved_wb = None
            try:
                excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
                sheet_names = excel_file.sheet_names
            except Exception:
                sheet_names = []

        parsed_sheets = {}
        
        for sheet_name in sheet_names:
            try:
                if resolved_wb is not None and sheet_name in resolved_wb:
                    # Construct DataFrame from resolved grid
                    df = pd.DataFrame(resolved_wb[sheet_name])
                else:
                    # Fallback to standard pandas read
                    excel_file = pd.ExcelFile(io.BytesIO(file_bytes))
                    df = excel_file.parse(sheet_name, header=None)
                
                # Clean sheet: remove completely empty rows/columns from borders
                df_cleaned = ExcelParser._clean_dataframe(df)
                
                if df_cleaned.empty:
                    continue
                
                # Determine header row(s) and set columns
                df_structured = ExcelParser._structure_dataframe(df_cleaned)
                
                # Generate clean markdown table
                markdown_table = ExcelParser._dataframe_to_markdown(df_structured, workbook_name, sheet_name)
                
                parsed_sheets[sheet_name] = {
                    "markdown": markdown_table,
                    "dataframe": df_structured,
                    "metadata": {
                        "workbook_name": workbook_name,
                        "sheet_name": sheet_name,
                        "rows": len(df_structured),
                        "columns": list(df_structured.columns)
                    }
                }
            except Exception as e:
                # Fallback simple reading if structured fails
                try:
                    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name)
                    markdown_table = f"[Workbook: {workbook_name}] [Sheet: {sheet_name}]\n\n" + df.to_markdown(index=False)
                    parsed_sheets[sheet_name] = {
                        "markdown": markdown_table,
                        "dataframe": df,
                        "metadata": {
                            "workbook_name": workbook_name,
                            "sheet_name": sheet_name,
                            "rows": len(df),
                            "columns": list(df.columns)
                        }
                    }
                except Exception as inner_e:
                    print(f"Error parsing sheet {sheet_name}: {inner_e}")
                    
        return {
            "workbook_name": workbook_name,
            "sheets": parsed_sheets
        }
    
    @staticmethod
    def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Removes leading/trailing completely empty rows and columns.
        """
        # Replace empty spaces with NaN
        df = df.map(lambda x: None if str(x).strip() == "" else x) if hasattr(df, 'map') else df.applymap(lambda x: None if str(x).strip() == "" else x)
        
        # Drop rows/cols that are entirely NaN
        df = df.dropna(how='all')
        if df.empty:
            return df
            
        df = df.dropna(axis=1, how='all')
        return df

    @staticmethod
    def _structure_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Identifies header and sets columns.
        Attempts to find a row containing years or headers.
        """
        df = df.reset_index(drop=True)
        
        # Look for the first row that contains column headers
        # Frequently, it's the row containing 'year', 'revenue', 'particulars', or numeric columns
        header_row_idx = 0
        max_non_nulls = 0
        
        # Check first 5 rows to determine the header
        for idx in range(min(5, len(df))):
            non_null_count = df.iloc[idx].notna().sum()
            # If the row has lots of string/year elements, it could be header
            row_vals = [str(x).lower() for x in df.iloc[idx].values if pd.notna(x)]
            has_keywords = any(any(kw in str(val) for kw in ["year", "particular", "revenue", "metric", "ratio", "component", "description", "item"]) for val in row_vals)
            
            if non_null_count > max_non_nulls or has_keywords:
                max_non_nulls = non_null_count
                header_row_idx = idx
                if has_keywords:
                    break
        
        # Retrieve column labels
        headers = []
        for col_idx in range(df.shape[1]):
            val = df.iloc[header_row_idx, col_idx]
            if pd.isna(val):
                headers.append(f"Column_{col_idx}")
            else:
                # Format to clean string, strip floats representing years e.g. 2022.0 -> 2022
                val_str = str(val).strip()
                if val_str.endswith(".0") and val_str[:-2].isdigit():
                    val_str = val_str[:-2]
                headers.append(val_str)
                
        # Handle duplicates in headers
        seen = {}
        unique_headers = []
        for h in headers:
            if h in seen:
                seen[h] += 1
                unique_headers.append(f"{h}_{seen[h]}")
            else:
                seen[h] = 0
                unique_headers.append(h)
                
        # Sub-slice dataframe to exclude headers and rows above it
        df_data = df.iloc[header_row_idx + 1:].copy()
        df_data.columns = unique_headers
        df_data = df_data.reset_index(drop=True)
        
        # Clean data rows where the first column is entirely empty (usually the labels)
        if df_data.shape[1] > 0:
            first_col = df_data.columns[0]
            df_data = df_data[df_data[first_col].notna()]
            
        return df_data

    @staticmethod
    def _dataframe_to_markdown(df: pd.DataFrame, workbook_name: str, sheet_name: str) -> str:
        """
        Converts a dataframe into a clean, aligned markdown table.
        """
        # Format floating values in data rows
        df_formatted = df.copy()
        for col in df_formatted.columns:
            try:
                # Attempt to format floats nicely
                df_formatted[col] = df_formatted[col].apply(ExcelParser._format_value)
            except Exception:
                pass
                
        markdown_str = f"[Workbook: {workbook_name}]\n[Sheet: {sheet_name}]\n\n"
        markdown_str += df_formatted.to_markdown(index=False)
        return markdown_str

    @staticmethod
    def _format_value(val: Any) -> Any:
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float)):
            # If it fits an integer, cast to int
            if isinstance(val, float) and val.is_integer():
                return int(val)
            # Format numbers to thousands separators or round to 2 decimals
            if abs(val) >= 1000:
                if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                    return f"{int(val):,}"
                return f"{val:,.2f}"
            elif isinstance(val, float):
                return round(val, 4)
        return str(val)

    @staticmethod
    def _parse_col_letter(col_str: str) -> int:
        col_idx = 0
        for char in col_str:
            col_idx = col_idx * 26 + (ord(char) - ord('A') + 1)
        return col_idx - 1

    @staticmethod
    def _resolve_cell(sheet_name: str, row_idx: int, col_idx: int, wb_data: dict, resolved_cache: dict, resolving_set: set = None) -> Any:
        if resolving_set is None:
            resolving_set = set()
            
        cell_key = (sheet_name, row_idx, col_idx)
        if cell_key in resolved_cache:
            return resolved_cache[cell_key]
            
        if cell_key in resolving_set:
            return None # Circular reference
            
        if sheet_name not in wb_data:
            return None
            
        grid = wb_data[sheet_name]
        if row_idx >= len(grid) or col_idx >= len(grid[row_idx]):
            return None
            
        raw_val = grid[row_idx][col_idx]
        if raw_val is None:
            return None
            
        val_str = str(raw_val).strip()
        if not val_str.startswith('='):
            resolved_cache[cell_key] = raw_val
            return raw_val
            
        resolving_set.add(cell_key)
        try:
            # Match single reference e.g., ='Data Sheet'!$B$16
            match_ref = re.match(r"^='?([^']*)'?!\$?([A-Z]+)\$?([0-9]+)$", val_str)
            if match_ref:
                ref_sheet = match_ref.group(1) or sheet_name
                ref_col = ExcelParser._parse_col_letter(match_ref.group(2))
                ref_row = int(match_ref.group(3)) - 1
                val = ExcelParser._resolve_cell(ref_sheet, ref_row, ref_col, wb_data, resolved_cache, resolving_set)
                resolved_cache[cell_key] = val
                return val
                
            expr = val_str[1:].strip()
            
            # Replace sheet ranges, e.g. 'Data Sheet'!$B$20:$B$24
            sheet_range_pattern = re.compile(r"'?([A-Za-z0-9_ &]+)'?!\$?([A-Z]+)\$?([0-9]+):\$?([A-Z]+)\$?([0-9]+)\b")
            def replace_sheet_range(match):
                ref_sheet = match.group(1)
                col1 = ExcelParser._parse_col_letter(match.group(2))
                row1 = int(match.group(3)) - 1
                col2 = ExcelParser._parse_col_letter(match.group(4))
                row2 = int(match.group(5)) - 1
                
                vals = []
                for r in range(min(row1, row2), max(row1, row2) + 1):
                    for c in range(min(col1, col2), max(col1, col2) + 1):
                        val = ExcelParser._resolve_cell(ref_sheet, r, c, wb_data, resolved_cache, resolving_set)
                        if isinstance(val, (int, float)):
                            vals.append(val)
                        elif val is not None:
                            try:
                                vals.append(float(val))
                            except ValueError:
                                pass
                return "+".join(map(str, vals)) if vals else "0"
                
            expr = sheet_range_pattern.sub(replace_sheet_range, expr)
            
            # Replace local ranges, e.g. $B$20:$B$24
            local_range_pattern = re.compile(r"(?<![!A-Za-z0-9_])\$?([A-Z]+)\$?([0-9]+):\$?([A-Z]+)\$?([0-9]+)\b")
            def replace_local_range(match):
                col1 = ExcelParser._parse_col_letter(match.group(1))
                row1 = int(match.group(2)) - 1
                col2 = ExcelParser._parse_col_letter(match.group(3))
                row2 = int(match.group(4)) - 1
                
                vals = []
                for r in range(min(row1, row2), max(row1, row2) + 1):
                    for c in range(min(col1, col2), max(col1, col2) + 1):
                        val = ExcelParser._resolve_cell(sheet_name, r, c, wb_data, resolved_cache, resolving_set)
                        if isinstance(val, (int, float)):
                            vals.append(val)
                        elif val is not None:
                            try:
                                vals.append(float(val))
                            except ValueError:
                                pass
                return "+".join(map(str, vals)) if vals else "0"
                
            expr = local_range_pattern.sub(replace_local_range, expr)
            
            # Replace sheet references, e.g. 'Data Sheet'!$B$16
            sheet_ref_pattern = re.compile(r"'?([A-Za-z0-9_ &]+)'?!\$?([A-Z]+)\$?([0-9]+)\b")
            def replace_sheet_ref(match):
                ref_sheet = match.group(1)
                ref_col = ExcelParser._parse_col_letter(match.group(2))
                ref_row = int(match.group(3)) - 1
                val = ExcelParser._resolve_cell(ref_sheet, ref_row, ref_col, wb_data, resolved_cache, resolving_set)
                return str(val) if val is not None else "0"
                
            expr = sheet_ref_pattern.sub(replace_sheet_ref, expr)
            
            # Replace local references, e.g. $C$4 or C$4
            ref_pattern = re.compile(r"(?<![!A-Za-z0-9_])\$?([A-Z]+)\$?([0-9]+)\b")
            def replace_local_ref(match):
                ref_col = ExcelParser._parse_col_letter(match.group(1))
                ref_row = int(match.group(2)) - 1
                val = ExcelParser._resolve_cell(sheet_name, ref_row, ref_col, wb_data, resolved_cache, resolving_set)
                return str(val) if val is not None else "0"
                
            expr = ref_pattern.sub(replace_local_ref, expr)
            
            # Evaluate standard Excel function SUM
            expr = re.sub(r"SUM\(([^)]+)\)", r"(\1)", expr, flags=re.I)
            
            # Clean comma separators inside SUM arguments which are now additions
            expr = expr.replace(",", "+")
            
            # Evaluate math expression safely
            if re.match(r"^[0-9\+\-\*\/\.\s\(\)]+$", expr):
                val = eval(expr)
                resolved_cache[cell_key] = val
                return val
        except Exception:
            pass
        finally:
            if cell_key in resolving_set:
                resolving_set.remove(cell_key)
            
        resolved_cache[cell_key] = raw_val
        return raw_val

