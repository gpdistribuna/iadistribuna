import os
import json
import hashlib
import PyPDF2
import shutil
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from utils.azure_storage import save_json_to_blob, load_json_from_blob, upload_blob, download_blob, delete_blob, list_blobs, blob_exists
import tempfile
import streamlit as st

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

#def create_vector_store(chunks: List[str], book_id: str) -> None:
#    """Crea un índice de vectores y lo guarda en disco."""
#    from langchain.embeddings.openai import OpenAIEmbeddings
#    from langchain.vectorstores import FAISS
    
   
#    openai_api_key = os.getenv("OPENAI_API_KEY")
#    if not openai_api_key:
#        raise ValueError("No se encontró la API key de OpenAI. Configura la variable de entorno OPENAI_API_KEY.")
    
    # Para OpenAI API 1.0+
#    embeddings = OpenAIEmbeddings(
#        model="text-embedding-3-large",
#        #model="text-embedding-3-small",
#        openai_api_key=openai_api_key
#    )
#    vector_store = FAISS.from_texts(chunks, embeddings)
    
    # Guardar el índice vectorial
#    book_vector_dir = os.path.join(VECTOR_DIR, book_id)
#    os.makedirs(book_vector_dir, exist_ok=True)
#    vector_store.save_local(book_vector_dir)
    
#    return book_vector_dir


#def get_book_info() -> Dict:
#    """Carga la información de los libros disponibles."""
#    if os.path.exists(BOOK_INFO_FILE):
#        with open(BOOK_INFO_FILE, 'r') as f:
#            return json.load(f)
#    return {}
def get_book_info() -> Dict:
    """Carga la información de los libros disponibles desde Azure Blob Storage."""
    return load_json_from_blob("books_info.json")

#def save_book_info(book_info: Dict) -> None:
#    """Guarda la información de los libros."""
#    with open(BOOK_INFO_FILE, 'w') as f:
#        json.dump(book_info, f)
def save_book_info(book_info: Dict) -> None:
    """Guarda la información de los libros en Azure Blob Storage."""
    save_json_to_blob(book_info, "books_info.json")

def process_book(pdf_path: str, title: str, author: str) -> str | None:
    """
    Procesa un libro PDF completo. Devuelve el book_id si tiene éxito, None si falla.
    Maneja excepciones internas y muestra errores en Streamlit.
    """
    try:
        print(f"[Debug] Procesando libro: Título='{title}', Autor='{author}'")
        # Generar ID único para el libro
        book_id = hashlib.md5((title + author + pdf_path).encode()).hexdigest() # Añadir pdf_path para más unicidad
        print(f"[Debug] Generado book_id: {book_id}")

        # 1. Extraer texto
        print("[Debug] Extrayendo texto del PDF...")
        text = extract_text_from_pdf(pdf_path)
        print(f"[Debug] Longitud del texto extraído: {len(text)}")
        if not text or len(text) < 10: # Añadir chequeo básico de longitud
            print("ERROR: Fallo al extraer texto o PDF vacío.")
            raise ValueError("Fallo al extraer texto del PDF o el PDF está vacío.")

        # 2. Dividir texto en chunks
        print("[Debug] Dividiendo texto en chunks...")
        chunks = split_text_into_chunks(text)
        print(f"[Debug] Dividido en {len(chunks)} chunks.")
        if not chunks:
             print("ERROR: La división del texto resultó en cero chunks.")
             raise ValueError("La división del texto resultó en cero chunks.")

        # 3. Crear y guardar vector store (puede lanzar excepción)
        print("[Debug] Creando vector store...")
        create_vector_store(chunks, book_id) # Ya no devuelve ruta, lanza excepción si falla
        print(f"[Debug] Vector store creado y subido a Azure para book_id: {book_id}")

        # 4. Guardar información del libro
        print("[Debug] Guardando información del libro...")
        book_info = get_book_info()
        book_info[book_id] = {"title": title, "author": author}
        if not save_book_info(book_info):
             # Considerar si esto debe ser un error fatal o solo una advertencia
             print(f"[Advertencia] Fallo al guardar la info del libro {book_id} en Azure.")
             st.warning(f"Se procesó el contenido del libro '{title}', pero hubo un problema al guardar su información general en Azure.")
             # Decide si continuar o fallar. Por ahora continuamos.
        else:
             print("[Debug] Información del libro guardada con éxito.")

        print(f"[Debug] Procesamiento del libro completado con éxito para book_id: {book_id}")
        return book_id # Devolver book_id si todo fue bien

    except Exception as e:
         # Capturar cualquier excepción durante el proceso
         print(f"ERROR durante el procesamiento del libro '{title}': {str(e)}")
         # Mostrar el error en la interfaz de Streamlit
         st.error(f"Error al procesar el libro '{title}': {str(e)}")
         return None # Indicar fallo devolviendo None

#def delete_book(book_id: str) -> bool:
#    """Elimina completamente un libro del sistema.
    
#    Args:
#        book_id: El ID del libro a eliminar
        
#    Returns:
#        bool: True si se eliminó correctamente, False en caso contrario
#    """
#    try:
        # Obtener información actual de libros
#        book_info = get_book_info()
        
        # Verificar que el libro exista
#        if book_id not in book_info:
#            return False
            
        # Eliminar el directorio de vectores
#        book_vector_dir = os.path.join(VECTOR_DIR, book_id)
#        if os.path.exists(book_vector_dir):
#            shutil.rmtree(book_vector_dir)
            
        # Eliminar la entrada del JSON
#        del book_info[book_id]
#        save_book_info(book_info)
        
#        return True
#    except Exception as e:
#        print(f"Error al eliminar libro: {str(e)}")
#        return False
def delete_book(book_id: str) -> bool:
    """Elimina completamente un libro del sistema."""
    try:
        # Obtener información actual de libros
        book_info = get_book_info()
        
        # Verificar que el libro exista
        if book_id not in book_info:
            return False
            
        # Eliminar todos los blobs asociados al libro
        blobs_to_delete = list_blobs(f"vector_stores/{book_id}")
        for blob_name in blobs_to_delete:
            delete_blob(blob_name)
            
        # Eliminar la entrada del JSON
        del book_info[book_id]
        save_book_info(book_info)
        
        return True
    except Exception as e:
        print(f"Error al eliminar libro: {str(e)}")
        return False


def get_default_book_id() -> str:
    """Obtiene el ID del primer libro disponible."""
    book_info = get_book_info()
    if book_info:
        return list(book_info.keys())[0]
    return ""