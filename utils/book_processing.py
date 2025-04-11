import os
import json
import hashlib
import PyPDF2
from typing import List, Dict, Any

# Configuración de rutas de almacenamiento
DATA_DIR = "data"
VECTOR_DIR = os.path.join(DATA_DIR, "vector_stores")
BOOK_INFO_FILE = os.path.join(DATA_DIR, "books_info.json")

# Crear directorios necesarios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extrae el texto completo de un archivo PDF."""
    text = ""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
    return text

def split_text_into_chunks(text: str) -> List[str]:
    """Divide el texto en fragmentos más pequeños."""
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def create_vector_store(chunks: List[str], book_id: str) -> None:
    """Crea un índice de vectores y lo guarda en disco."""
    from langchain.embeddings import OpenAIEmbeddings
    from langchain.vectorstores import FAISS
    
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_texts(chunks, embeddings)
    
    # Guardar el índice vectorial
    book_vector_dir = os.path.join(VECTOR_DIR, book_id)
    os.makedirs(book_vector_dir, exist_ok=True)
    vector_store.save_local(book_vector_dir)
    
    return book_vector_dir

def get_book_info() -> Dict:
    """Carga la información de los libros disponibles."""
    if os.path.exists(BOOK_INFO_FILE):
        with open(BOOK_INFO_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_book_info(book_info: Dict) -> None:
    """Guarda la información de los libros."""
    with open(BOOK_INFO_FILE, 'w') as f:
        json.dump(book_info, f)

def process_book(pdf_path: str, title: str, author: str) -> str:
    """Procesa un libro y guarda su índice vectorial."""
    import streamlit as st
    
    # Crear un ID único para el libro
    book_id = hashlib.md5(f"{title}_{author}".encode()).hexdigest()
    
    # Extraer texto del PDF
    st.info("Extrayendo texto del PDF...")
    text = extract_text_from_pdf(pdf_path)
    
    # Dividir en fragmentos
    st.info("Dividiendo el texto en fragmentos...")
    chunks = split_text_into_chunks(text)
    
    # Crear y guardar el índice vectorial
    st.info("Creando índice vectorial...")
    vector_dir = create_vector_store(chunks, book_id)
    
    # Actualizar la información del libro
    book_info = get_book_info()
    book_info[book_id] = {
        "title": title,
        "author": author,
        "vector_dir": vector_dir
    }
    save_book_info(book_info)
    
    return book_id

def get_default_book_id() -> str:
    """Obtiene el ID del primer libro disponible."""
    book_info = get_book_info()
    if book_info:
        return list(book_info.keys())[0]
    return ""