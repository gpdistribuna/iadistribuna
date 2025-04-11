# Sistema de QA con Libros - Versión con acceso de administrador
# Características:
# - Página de administrador protegida con contraseña para subir libros
# - Página de usuario para consultar libros ya procesados
# - Almacenamiento persistente de índices vectoriales

import os
import PyPDF2
import hashlib
import json
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import streamlit as st

# Configurar la API key de OpenAI
os.environ["OPENAI_API_KEY"] = "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"  # Reemplaza con tu API key

# Configuración de rutas de almacenamiento
DATA_DIR = "data"
VECTOR_DIR = os.path.join(DATA_DIR, "vector_stores")
BOOK_INFO_FILE = os.path.join(DATA_DIR, "books_info.json")
#ADMIN_PASSWORD = "admin123"  # Cambia esto por una contraseña segura

# Crear directorios necesarios si no existen
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(VECTOR_DIR, exist_ok=True)

# Funciones de extracción y procesamiento de texto
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
    """Divide el texto en fragmentos más pequeños para un procesamiento eficiente."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    return text_splitter.split_text(text)

def create_vector_store(chunks: List[str], book_id: str) -> None:
    """Crea un índice de vectores y lo guarda en disco."""
    embeddings = OpenAIEmbeddings()
    vector_store = FAISS.from_texts(chunks, embeddings)
    
    # Guardar el índice vectorial
    book_vector_dir = os.path.join(VECTOR_DIR, book_id)
    os.makedirs(book_vector_dir, exist_ok=True)
    vector_store.save_local(book_vector_dir)
    
    return book_vector_dir

def load_vector_store(book_id: str) -> FAISS:
    """Carga un índice vectorial previamente guardado."""
    book_vector_dir = os.path.join(VECTOR_DIR, book_id)
    embeddings = OpenAIEmbeddings()
    return FAISS.load_local(book_vector_dir, embeddings, allow_dangerous_deserialization=True)

def setup_rag(vector_store: FAISS) -> RetrievalQA:
    """Configura el sistema RAG con el índice de vectores."""
    # Plantilla de prompt específica para responder preguntas sobre libros
    template = """
    Eres un asistente experto que responde preguntas sobre un libro específico.
    Tu objetivo es proporcionar respuestas precisas basadas únicamente en el contenido del libro.
    
    Contexto del libro:
    {context}
    
    Pregunta: {question}
    
    Instrucciones:
    - Responde solo con información que esté explícitamente presente en el contexto proporcionado.
    - Si la información no está en el contexto, indica: "No puedo responder esta pregunta basándome en el contenido del libro."
    - No inventes información ni uses conocimiento externo.
    - Cita capítulos o secciones específicas cuando sea posible.
    - Proporciona una respuesta clara, concisa y directa.
    
    Respuesta:
    """
    
    PROMPT = PromptTemplate(
        template=template, 
        input_variables=["context", "question"]
    )
    
    # Configurar el modelo de lenguaje
    llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
    
    # Configurar el sistema RAG
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 4}),
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    return qa_chain

def answer_question(qa_chain: RetrievalQA, question: str) -> str:
    """Procesa una pregunta y genera una respuesta basada en el contenido del libro."""
    return qa_chain.run(question)

# Funciones para gestión de libros
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

# Secciones de la interfaz de usuario
def admin_login():
    """Pantalla de login para administradores."""
    st.subheader("Acceso de Administrador")
    password = st.text_input("Contraseña", type="password")
    
    if st.button("Iniciar sesión"):
        if password == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.success("Acceso concedido")
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

def admin_panel():
    """Panel de administración para subir y procesar libros."""
    st.subheader("Panel de Administrador")
    
    if st.button("Cerrar sesión", key="logout"):
        st.session_state.admin_logged_in = False
        st.rerun()
    
    st.markdown("---")
    st.subheader("Subir nuevo libro")
    
    # Formulario para subir libro
    title = st.text_input("Título del libro")
    author = st.text_input("Autor")
    uploaded_file = st.file_uploader("Subir PDF del libro", type="pdf")
    
    process_button = st.button("Procesar Libro")
    
    if process_button and uploaded_file and title and author:
        # Guardar PDF temporalmente
        with open("temp_book.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Procesar el libro
        with st.spinner("Procesando libro... esto puede tomar varios minutos dependiendo del tamaño del libro"):
            book_id = process_book("temp_book.pdf", title, author)
            
        st.success(f"¡Libro '{title}' procesado correctamente!")
        
        # Limpiar después de procesar
        if os.path.exists("temp_book.pdf"):
            os.remove("temp_book.pdf")
    
    # Mostrar libros existentes
    st.markdown("---")
    st.subheader("Libros disponibles")
    
    book_info = get_book_info()
    if book_info:
        for book_id, info in book_info.items():
            st.markdown(f"**{info['title']}** por {info['author']}")
    else:
        st.info("No hay libros disponibles. Sube algunos libros para comenzar.")

def user_interface():
    """Interfaz para que los usuarios consulten los libros disponibles."""
    st.subheader("Consulta sobre Libros")
    
    # Obtener lista de libros disponibles
    book_info = get_book_info()
    
    if not book_info:
        st.info("No hay libros disponibles para consultar en este momento.")
        return
    
    # Selección de libro
    book_titles = {book_id: info["title"] for book_id, info in book_info.items()}
    selected_book_id = st.selectbox(
        "Selecciona un libro para consultar:",
        options=list(book_titles.keys()),
        format_func=lambda x: book_titles[x]
    )
    
    # Mostrar información del libro seleccionado
    if selected_book_id:
        selected_book = book_info[selected_book_id]
        st.markdown(f"**Libro seleccionado:** {selected_book['title']} por {selected_book['author']}")
        
        # Sección para hacer preguntas
        st.markdown("---")
        st.subheader("Hacer una pregunta")
        question = st.text_input("Escribe tu pregunta sobre el libro:")
        
        if st.button("Buscar respuesta") and question:
            with st.spinner("Buscando respuesta..."):
                # Cargar el índice vectorial del libro
                vector_store = load_vector_store(selected_book_id)
                
                # Configurar el sistema RAG
                qa_system = setup_rag(vector_store)
                
                # Generar respuesta
                answer = answer_question(qa_system, question)
                
                # Mostrar respuesta
                st.markdown("### Respuesta:")
                st.write(answer)

# Aplicación principal
def main():
    st.title("Sistema de Consultas sobre Libros")
    
    # Inicializar estado de la sesión
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False
    
    # Barra lateral para navegación
    with st.sidebar:
        st.title("Navegación")
        
        if st.session_state.admin_logged_in:
            st.success("Modo Administrador")
            page = "Admin"
        else:
            page = st.radio("Ir a:", ["Usuario", "Admin"])
            
            if page == "Admin" and not st.session_state.admin_logged_in:
                admin_login()
                page = "Usuario"  # Redirigir a Usuario si no está autenticado
    
    # Mostrar la página correspondiente
    if page == "Admin" and st.session_state.admin_logged_in:
        admin_panel()
    else:
        user_interface()

if __name__ == "__main__":
    main()