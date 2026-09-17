from pathlib import Path

from dotenv import load_dotenv

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_qdrant import QdrantVectorStore
from app.routes.query import COLLECTION_NAME, QDRANT_URL, HuggingFaceEmbeddings

# Legacy OpenAI embeddings (intentionally disabled):
# from langchain_openai import OpenAIEmbeddings
# embedding_model = OpenAIEmbeddings(
#     model="text-embedding-3-large", api_key=os.getenv("OPENAI_API_KEY")
# )

load_dotenv()

pdf_path = Path(__file__).parent / "data" /"sample.pdf"
#PDF Loader
loader = PyPDFLoader(str(pdf_path))
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=400
)
chunks = text_splitter.split_documents(documents=docs)

# Create a Qdrant vector store with the same Hugging Face embedding model as queries.
vector_store = QdrantVectorStore.from_documents(
    documents=chunks,
    embedding=HuggingFaceEmbeddings(),
    collection_name=COLLECTION_NAME,
    url=QDRANT_URL,
)
print("Vector store created and documents embedded successfully.")

