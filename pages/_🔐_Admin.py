import streamlit as st
import os
from utils.book_processing import get_book_info, process_book, save_book_info
from utils.auth import check_password
from utils.book_processing import get_book_info, process_book, save_book_info, delete_book

def load_css():
    with open(".streamlit/style.css") as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

st.set_page_config(
    page_title="Admin - Sistema de Libros",
    page_icon="🔐",
    initial_sidebar_state="collapsed"
    
)

def admin_panel():
    left_co, cent_co, last_co = st.columns(3)
    with cent_co:
        st.image("https://distribuna.com/wp-content/uploads/2021/05/GrupoDistribuna_2021_Verde3.png")
    st.title("Panel de Administración 🔐")
    
    # Si no está autenticado, mostrar pantalla de login
    if not check_password():
        return
    
    st.success("Acceso concedido. Bienvenido administrador.")
    
    st.markdown("---")
    st.subheader("Subir nuevo libro")
    
    # Formulario para subir libro
    with st.form("upload_book_form"):
        title = st.text_input("Título del libro")
        author = st.text_input("Autor")
        uploaded_file = st.file_uploader("Subir PDF del libro", type="pdf")
        
        submit_button = st.form_submit_button("📤 Procesar Libro")
    
    if submit_button and uploaded_file and title and author:
        # Guardar PDF temporalmente
        with open("temp_book.pdf", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Procesar el libro
        with st.spinner("Procesando libro... esto puede tomar varios minutos dependiendo del tamaño del libro"):
            book_id = process_book("temp_book.pdf", title, author)
            
        st.success(f"¡Libro '{title}' procesado correctamente!")
        
        # Mostrar enlace para acceder al libro
        st.markdown(f"Enlace para usuarios: [Consultar {title}](/Usuario?book_id={book_id})")
        
        # Limpiar después de procesar
        if os.path.exists("temp_book.pdf"):
            os.remove("temp_book.pdf")
    
    # Mostrar libros existentes
    st.markdown("---")
    st.subheader("Libros disponibles")
    
    book_info = get_book_info()
    if book_info:
        for book_id, info in book_info.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{info['title']}** por {info['author']}")
            
            with col2:
                st.markdown(f"[🔗 Enlace](/Usuario?book_id={book_id})")
            
            with col3:
                if st.button("🗑️ Eliminar", key=f"delete_{book_id}"):
        # Usar la función de eliminación completa
                    if delete_book(book_id):
                        st.success(f"Libro '{info['title']}' eliminado correctamente.")
        else:
            st.error(f"Error al eliminar el libro '{info['title']}'.")
        st.rerun()
    else:
        st.info("No hay libros disponibles. Sube algunos libros para comenzar.")

if __name__ == "__main__":
    admin_panel()