from typing import List, Dict, Any

CHAT_SYSTEM_PROMPT = """
You are an expert AI Financial Analyst assistant.
You are helping a user analyze a financial workbook containing several spreadsheets (Balance Sheet, P&L, Cash Flow, etc.).
You are provided with highly relevant spreadsheets extracted from the workbook as context.

### CONTEXT SHEETS:
{context}

### INSTRUCTIONS:
1. Answer the user's question with professional financial clarity, utilizing the figures from the context.
2. Ground your answers strictly in the data. If the information is not present in the sheets, state that you cannot find it in the workbook. Do NOT make up numbers or guess.
3. ALWAYS cite the sheet name (e.g., "[Sheet: Balance Sheet]") and specific year/row when you reference a number.
4. Keep your explanations analytical and structured.
5. If the user asks for calculations (like ratios), show the formula and the raw numbers you used from the sheets before presenting the final result.
"""

def build_chat_prompt(query: str, context: str, chat_history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Constructs the list of messages for the OpenAI Chat Completion API.
    Args:
        query: The user's query.
        context: The combined markdown sheets retrieved for this query.
        chat_history: List of dicts, e.g., [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    Returns:
        List[Dict[str, str]]: Messages list.
    """
    messages = []
    
    # 1. System instruction
    messages.append({
        "role": "system",
        "content": CHAT_SYSTEM_PROMPT.format(context=context)
    })
    
    # 2. History (keep last 6 turn-pairs to avoid token bloat)
    for msg in chat_history[-12:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
        
    # 3. Current User Question
    messages.append({
        "role": "user",
        "content": query
    })
    
    return messages
