import uuid
import tiktoken
from typing import List, Dict, Any, Tuple

class ParentChildChunker:
    """
    Chunks large sheet markdown tables into row-based child chunks of 150-250 tokens,
    while preserving the full sheet markdown as parent documents.
    """
    def __init__(self, target_chunk_tokens: int = 200, model_name: str = "gpt-4o"):
        try:
            self.encoder = tiktoken.encoding_for_model(model_name)
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")
        self.target_chunk_tokens = target_chunk_tokens

    def chunk_sheet(self, sheet_markdown: str, workbook_name: str, sheet_name: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Chunks a single sheet's markdown.
        Returns:
            parent_doc: Dict containing {id, text, metadata}
            child_chunks: List of Dicts, each containing {id, parent_id, text, metadata}
        """
        parent_id = str(uuid.uuid4())
        parent_doc = {
            "id": parent_id,
            "text": sheet_markdown,
            "metadata": {
                "workbook_name": workbook_name,
                "sheet_name": sheet_name,
                "type": "parent"
            }
        }

        # Parse markdown lines
        lines = [line.strip() for line in sheet_markdown.split('\n')]
        
        # Identify headers and separator lines
        table_lines = []
        metadata_lines = []
        
        for line in lines:
            if line.startswith('|'):
                table_lines.append(line)
            elif line:
                metadata_lines.append(line)
                
        if len(table_lines) < 2:
            # If not a table, fall back to simple text chunking
            child_chunks = self._fallback_chunking(sheet_markdown, parent_id, workbook_name, sheet_name)
            return parent_doc, child_chunks

        # Typically table_lines[0] is column headers, table_lines[1] is |---|---|
        header_row = table_lines[0]
        separator_row = table_lines[1]
        data_rows = table_lines[2:]
        
        child_chunks = []
        current_rows = []
        chunk_idx = 0
        
        # We group rows such that each chunk is around 150-250 tokens
        # A chunk contains metadata, headers, separator, and data_rows
        def make_chunk_text(rows: List[str], start_r: int, end_r: int) -> str:
            prefix = f"[Workbook: {workbook_name}] [Sheet: {sheet_name}] [Rows: {start_r}-{end_r}]\n"
            table_snippet = "\n".join([header_row, separator_row] + rows)
            return f"{prefix}\n{table_snippet}"

        start_row_idx = 1
        for i, row in enumerate(data_rows):
            current_rows.append(row)
            # Estimate tokens
            temp_text = make_chunk_text(current_rows, start_row_idx, start_row_idx + len(current_rows) - 1)
            tokens_count = len(self.encoder.encode(temp_text))
            
            # If we reach or exceed the target token size, or if it is the last row, flush the chunk
            if tokens_count >= self.target_chunk_tokens or i == len(data_rows) - 1:
                # If chunk is too large and has multiple rows, back off one row unless it's a single row
                if tokens_count > self.target_chunk_tokens + 100 and len(current_rows) > 1:
                    last_row = current_rows.pop()
                    chunk_text = make_chunk_text(current_rows, start_row_idx, start_row_idx + len(current_rows) - 1)
                    actual_tokens = len(self.encoder.encode(chunk_text))
                    
                    child_chunks.append({
                        "id": f"{parent_id}_child_{chunk_idx}",
                        "parent_id": parent_id,
                        "text": chunk_text,
                        "metadata": {
                            "workbook_name": workbook_name,
                            "sheet_name": sheet_name,
                            "rows": f"{start_row_idx}-{start_row_idx + len(current_rows) - 1}",
                            "tokens": actual_tokens,
                            "type": "child"
                        }
                    })
                    chunk_idx += 1
                    start_row_idx += len(current_rows)
                    current_rows = [last_row]
                else:
                    child_chunks.append({
                        "id": f"{parent_id}_child_{chunk_idx}",
                        "parent_id": parent_id,
                        "text": temp_text,
                        "metadata": {
                            "workbook_name": workbook_name,
                            "sheet_name": sheet_name,
                            "rows": f"{start_row_idx}-{start_row_idx + len(current_rows) - 1}",
                            "tokens": tokens_count,
                            "type": "child"
                        }
                    })
                    chunk_idx += 1
                    start_row_idx += len(current_rows)
                    current_rows = []

        return parent_doc, child_chunks

    def _fallback_chunking(self, text: str, parent_id: str, workbook_name: str, sheet_name: str) -> List[Dict[str, Any]]:
        # Fallback character-based/token-based chunking
        tokens = self.encoder.encode(text)
        child_chunks = []
        chunk_idx = 0
        step = self.target_chunk_tokens
        
        for idx in range(0, len(tokens), step):
            chunk_tokens = tokens[idx:idx + step]
            chunk_text = self.encoder.decode(chunk_tokens)
            prefix = f"[Workbook: {workbook_name}] [Sheet: {sheet_name}] [Part: {chunk_idx + 1}]\n\n"
            full_chunk_text = prefix + chunk_text
            
            child_chunks.append({
                "id": f"{parent_id}_child_{chunk_idx}",
                "parent_id": parent_id,
                "text": full_chunk_text,
                "metadata": {
                    "workbook_name": workbook_name,
                    "sheet_name": sheet_name,
                    "tokens": len(self.encoder.encode(full_chunk_text)),
                    "type": "child"
                }
            })
            chunk_idx += 1
            
        return child_chunks
