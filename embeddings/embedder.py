import os
import time
from typing import List
from openai import OpenAI

class OpenAIEmbedder:
    """
    Interacts with OpenAI API to generate high-quality text embeddings
    using the text-embedding-3-large model.
    """
    def __init__(self, model_name: str = None, api_key: str = None):
        self.model_name = model_name or os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            # We will allow instantiation without API key but fail gracefully when embedding is called
            pass
            
    def _get_client(self) -> OpenAI:
        if not self.api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set in environment or constructor.")
            self.api_key = api_key
        return OpenAI(api_key=self.api_key)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embeds a list of documents (child chunks).
        """
        if not texts:
            return []
            
        client = self._get_client()
        embeddings = []
        
        # OpenAI limits batch sizes, we will batch texts in chunks of 100
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # Simple retry logic
            max_retries = 3
            backoff_factor = 2
            
            for attempt in range(max_retries):
                try:
                    response = client.embeddings.create(
                        input=batch_texts,
                        model=self.model_name
                    )
                    embeddings.extend([item.embedding for item in response.data])
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(backoff_factor ** attempt)
                    
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """
        Embeds a single query string.
        """
        res = self.embed_documents([text])
        return res[0] if res else []
