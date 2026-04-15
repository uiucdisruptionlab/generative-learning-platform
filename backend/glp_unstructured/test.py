import os, json

from pdf_text_extractor import PDFTextExtractor
from text_chunker import TextChunker

extractor = PDFTextExtractor(os.getenv("UNSTRUCTURED_API_KEY"))
chunker = TextChunker(chunk_size=500, chunk_overlap=100) 

filename = "./input_files/canvas_api_sow.pdf"
OUTPUT_DIR = "./output_files/"
OUTPUT_FILE_PATH = os.path.join(OUTPUT_DIR, "chunks.json")


os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    texts = extractor.extract_texts(filename)
    chunks = chunker.chunk_texts(texts)
    
    
    if chunks:
        print(chunks[0])
    else:
        print("No chunks created")

    with open(OUTPUT_FILE_PATH, "w") as file:
        json.dump(chunks, file, indent=2)

except Exception as e:
    print(e)