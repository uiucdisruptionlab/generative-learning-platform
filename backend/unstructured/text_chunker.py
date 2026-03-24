from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TextChunker:
    """
    Chunks text elements semantically using LangChain.
    Handles long texts by splitting at natural boundaries.
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],  
            keep_separator=True
        )

    def chunk_texts(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Input: List of {'text': str, 'metadata': dict}
        Output: List of {'chunk': str, 'metadata': dict} (with updated metadata for chunk index)
        """
        chunks = []
        for i, item in enumerate(texts):
            text = item['text']
            metadata = item['metadata'].copy()
            
            text_chunks = self.splitter.split_text(text)
            
            for j, chunk in enumerate(text_chunks):
                chunk_metadata = metadata.copy()
                chunk_metadata['chunk_index'] = j
                chunk_metadata['original_element_index'] = i
                chunks.append({
                    'chunk': chunk,
                    'metadata': chunk_metadata
                })
        
        return chunks