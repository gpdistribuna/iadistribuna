import streamlit as st
import os
import json
from langchain.embeddings import OpenAIEmbeddings
from utils.book_processing import get_book_info, get_default_book_id
from utils.qa_system import load_vector_store, setup_rag, answer_question

def load_css():
    with open(".streamlit/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Consulta de Libros",
    page_icon="📚",
    initial_sidebar_state="collapsed"    
)

def user_interface():
    # Limpiar caché al iniciar la página para asegurar datos actualizados
    st.cache_data.clear()
    st.cache_resource.clear()
    
    left_co, cent_co, last_co = st.columns(3)
    with cent_co:
        st.image("https://distribuna.com/wp-content/uploads/2021/05/GrupoDistribuna_2021_Verde3.png")
    st.title("Consulta de Libros 📚")
    
    # Obtener lista de libros disponibles
    book_info = get_book_info()
    
    if not book_info:
        st.info("No hay libros disponibles para consultar en este momento.")
        return
    
    # Manejar parámetros de URL de forma más robusta
    try:
        query_params = st.query_params
        # Obtener book_id del parámetro URL
        book_id = query_params.get("book_id", None)
              
        # Verificar si el book_id existe en los libros disponibles
        if not book_id or book_id not in book_info:
            book_id = get_default_book_id()
            if book_id not in book_info and book_info:
                # Si el default también es inválido, usar el primer libro
                book_id = list(book_info.keys())[0]
    except Exception as e:
        st.error(f"Error procesando parámetros: {str(e)}")
        # Usar el primer libro como fallback
        if book_info:
            book_id = list(book_info.keys())[0]
        else:
            st.error("Error al cargar libros.")
            return
      
    # Mostrar información del libro seleccionado
    selected_book = book_info[book_id]
    st.header(f"📖 {selected_book['title']}")
    st.subheader(f"por {selected_book['author']}")
    
    # Sección para hacer preguntas
    st.markdown("---")
    st.markdown("### Haz tu pregunta sobre este libro:")
    question = st.text_area("", height=100, placeholder="Escribe tu pregunta aquí...")
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        search_button = st.button("🔍 Buscar", type="primary", use_container_width=True)
    
    with col2:
        # Inicializar historial específico para cada libro
        if "history" not in st.session_state:
            st.session_state.history = {}
        
        if book_id not in st.session_state.history:
            st.session_state.history[book_id] = []
            
        clear_button = st.button("🗑️ Limpiar historial", use_container_width=True)
        if clear_button:
            st.session_state.history[book_id] = []
            st.rerun()
    
    if search_button and question:
        with st.spinner("Buscando respuesta..."):
            try:
                # Verificar la API key de OpenAI
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    st.error("No se encontró la API key de OpenAI. Contacte al administrador del sistema.")
                else:
                    # Cargar el índice vectorial del libro
                    vector_store = load_vector_store(book_id)
                    
                    # Configurar el sistema RAG
                    qa_system = setup_rag(vector_store)
                    
                    # Generar respuesta
                    answer = answer_question(qa_system, question)
                    
                    # Guardar en historial específico del libro
                    st.session_state.history[book_id].append({
                        "question": question,
                        "answer": answer
                    })
            except Exception as e:
                st.error(f"Error al procesar tu pregunta: {str(e)}")
    
    # Mostrar historial de preguntas y respuestas para el libro actual
    if book_id in st.session_state.history and st.session_state.history[book_id]:
        st.markdown("---")
        st.markdown("### Historial de consultas:")
        
        for i, qa in enumerate(reversed(st.session_state.history[book_id])):
            with st.expander(f"Pregunta: {qa['question']}", expanded=(i == 0)):
                st.markdown(qa['answer'])

if __name__ == "__main__":
    user_interface()