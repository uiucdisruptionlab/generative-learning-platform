import os
from typing import List, Dict, Any

import unstructured_client
from unstructured_client.models import operations, shared


class PDFTextExtractor:
    """
    Extracts text strings from PDFs using Unstructured API.
    Returns list of text elements with metadata.
    """

    def __init__(self, unstructured_api_key: str):
        self.unstructured_client = unstructured_client.UnstructuredClient(api_key_auth=unstructured_api_key)

    def extract_texts(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Parse PDF and extract text elements.
        Returns list of dicts: {'text': str, 'metadata': dict}
        """
        with open(pdf_path, "rb") as f:
            files_content = f.read()

        req = operations.PartitionRequest(
            partition_parameters=shared.PartitionParameters(
                files=shared.Files(
                    content=files_content,
                    file_name=os.path.basename(pdf_path),
                ),
                strategy=shared.Strategy.VLM,
                vlm_model="gpt-4o",
                vlm_model_provider="openai",
                languages=['eng'],
                split_pdf_page=True,
                split_pdf_allow_failed=True,
                split_pdf_concurrency_level=15
            ),
        )

        res = self.unstructured_client.general.partition(request=req)
        texts = []
        for element in res.elements:
            element_dict = element  
            text = element_dict.get('text', '').strip()
            if text:  
                texts.append({
                    'text': text,
                    'metadata': element_dict.get('metadata', {})
                })
            # print(f"Text Extracted: {text} \n")
        return texts