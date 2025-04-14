import streamlit as st
import os
from utils.book_processing import get_book_info

def load_css():
    with open(".streamlit/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Distribuna IA",
    page_icon="📚",
    initial_sidebar_state="collapsed"
)

def main():
    left_co, cent_co, last_co = st.columns(3)
    with cent_co:
        st.image("https://distribuna.com/wp-content/uploads/2021/05/GrupoDistribuna_2021_Verde3.png")
    st.title("Grupo Distribuna IA 📚")
    
    st.markdown("""
    Bienvenido al sistema de consultas de Grupo Distribuna. Este sistema te permite hacer preguntas
    sobre libros específicos y recibir respuestas basadas únicamente en su contenido.
    
    ### Información importante:
     - Para consultar un libro, necesitas un enlace específico proporcionado por el administrador.
    - Cada enlace te da acceso exclusivo al contenido de un libro en particular.
    - Sin el enlace correcto, no podrás acceder a la vista de consultas.
    
    ### ¿Necesitas acceso?
    Si necesitas acceder a un libro disponible en nuestro sistema, contacta con el administrador para recibir tu enlace personalizado.
    
    """)
    
    # Mostrar libros disponibles
    st.subheader("Libros disponibles en el sistema:")
    
    book_info = get_book_info()
    if book_info:
        for book_id, info in book_info.items():
            st.markdown(f"- **{info['title']}** por {info['author']}")
    else:
        st.info("No hay libros disponibles en el sistema actualmente.")

if __name__ == "__main__":
    main()