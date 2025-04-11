import streamlit as st
import os
from dotenv import load_dotenv

# Cargar variables de entorno si existe un archivo .env
load_dotenv()

# Comprobar si existe la API key de OpenAI
if not os.getenv("OPENAI_API_KEY"):
    print("ADVERTENCIA: No se encontró la API key de OpenAI. Las funciones de IA no funcionarán correctamente.")

# Obtener la contraseña desde las variables de entorno o usar una por defecto
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

def check_password():
    """Verifica la contraseña del administrador.
    Devuelve True si está autenticado, False en caso contrario."""
    
    # Si ya está autenticado, no mostrar el formulario
    if st.session_state.get("authenticated", False):
        return True
    
    # Mostrar formulario de autenticación
    st.subheader("Acceso de Administrador")
    
    # Crear dos columnas para centrar el formulario
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Iniciar sesión")
            
            if submitted:
                if password == ADMIN_PASSWORD:
                    st.session_state.authenticated = True
                    return True
                else:
                    st.error("Contraseña incorrecta")
                    return False
    
    return False