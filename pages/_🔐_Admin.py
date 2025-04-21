import streamlit as st
import os
from utils.book_processing import get_book_info, process_book, save_book_info, delete_book
from utils.auth import check_password

# pages/_🔐_Admin.py

import streamlit as st
import os
# Asegúrate de importar todas las funciones necesarias
from utils.book_processing import get_book_info, process_book, delete_book
from utils.auth import check_password # Asumiendo que check_password está en auth.py

# Función opcional para cargar CSS si existe el archivo
def load_css():
    """Carga un archivo CSS si existe en la ruta especificada."""
    style_path = ".streamlit/style.css"
    if os.path.exists(style_path):
        try:
            with open(style_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
        except FileNotFoundError:
            print(f"Advertencia: Archivo CSS no encontrado en {style_path}")
        except Exception as e:
             print(f"Error al cargar CSS: {e}")
    # else:
    #      print(f"Nota: Ruta para CSS no existe: {style_path}")

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Admin - Sistema de Libros",
    page_icon="🔐",
    initial_sidebar_state="collapsed"
)

# Cargar CSS personalizado
load_css()

def admin_panel():
    """Función principal que renderiza el panel de administración."""

    # Mostrar logo centrado
    left_co, cent_co, last_co = st.columns(3)
    with cent_co:
        try:
             st.image("https://distribuna.com/wp-content/uploads/2021/05/GrupoDistribuna_2021_Verde3.png", width=250) # Ajustar tamaño si es necesario
        except Exception as img_err:
             print(f"No se pudo cargar la imagen: {img_err}")
             st.warning("No se pudo cargar la imagen del logo.")

    st.title("Panel de Administración 🔐")

    # --- Verificación de Autenticación ---
    # Inicializar estado de autenticación si no existe
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    # Si no está autenticado, mostrar formulario de login y detener
    if not st.session_state.authenticated:
         # La función check_password() maneja la lógica y muestra el formulario
         if check_password():
             # Si el login es exitoso, check_password actualiza st.session_state
             # y devuelve True. Hacemos rerun para recargar la página ya autenticado.
             st.rerun()
         else:
             # Si no se autentica (o no ha enviado el formulario), detener la ejecución aquí.
             return

    # --- Panel de Administración (Solo si está autenticado) ---
    st.success("Acceso concedido. Bienvenido administrador.")

    st.markdown("---")
    st.subheader("Subir nuevo libro")

    # Formulario para subir un nuevo libro
    # clear_on_submit=True limpia los campos después de enviar exitosamente
    with st.form("upload_book_form", clear_on_submit=True):
        title = st.text_input("Título del libro")
        author = st.text_input("Autor del libro")
        uploaded_file = st.file_uploader("Seleccionar archivo PDF", type="pdf")
        submitted = st.form_submit_button("Procesar Libro")

        if submitted:
            if uploaded_file and title and author:
                # Usar un nombre temporal único para evitar colisiones si varios usan la app
                temp_pdf_path = f"temp_{uploaded_file.name}"
                try:
                    # Guardar el archivo PDF subido temporalmente en el servidor
                    with open(temp_pdf_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())

                    # Mostrar un indicador de progreso mientras se procesa
                    with st.spinner(f"Procesando '{title}'... Esto puede tardar varios minutos."):
                        # Llamar a la función de procesamiento y verificar el resultado
                        # process_book ahora devuelve book_id en éxito, None en fallo
                        book_id = process_book(temp_pdf_path, title, author)

                    # Comprobar si el procesamiento fue exitoso
                    if book_id:
                        st.success(f"¡Libro '{title}' procesado y añadido con éxito!")
                        # Mostrar el enlace relativo para la página del usuario
                        st.markdown(f"Enlace para usuarios: [Consultar {title}](/Usuario?book_id={book_id})")
                        # Limpiar caché (opcional, pero puede ayudar a asegurar que la lista se actualice)
                        # Usar con precaución, borra todo el caché
                        # st.cache_data.clear()
                        # st.cache_resource.clear()
                        # Forzar la re-ejecución del script para refrescar la lista de libros
                        st.rerun()
                    else:
                        # El error específico ya debería haberse mostrado dentro de process_book
                        # usando st.error(). Se podría añadir un mensaje genérico si se desea.
                         st.warning("El procesamiento del libro falló. Revisa los logs del servidor para más detalles si el error no fue claro.")
                         pass # No hacer nada más aquí si falló

                except Exception as e:
                     st.error(f"Ocurrió un error inesperado al manejar el archivo subido: {str(e)}")
                finally:
                     # Asegurarse de eliminar SIEMPRE el archivo temporal
                     if os.path.exists(temp_pdf_path):
                         try:
                             os.remove(temp_pdf_path)
                         except OSError as e_del:
                             print(f"Error al eliminar archivo temporal {temp_pdf_path}: {e_del}")

            else:
                # Si no se completaron todos los campos del formulario
                st.error("Por favor, completa todos los campos: Título, Autor y Archivo PDF.")

    # --- Mostrar Libros Existentes ---
    st.markdown("---")
    st.subheader("Libros disponibles")

    # Obtener la información de los libros (podría beneficiarse de caché aquí)
    book_info = get_book_info()

    if not book_info:
        st.info("No hay libros disponibles. Sube algunos libros para comenzar.")
    else:
        # Ordenar los libros alfabéticamente por título para una vista consistente
        try:
            sorted_book_items = sorted(book_info.items(), key=lambda item: item[1].get('title', '').lower())
        except AttributeError: # Manejar caso donde 'info' no sea diccionario o falte 'title'
             st.error("Error al ordenar la lista de libros.")
             sorted_book_items = book_info.items()


        # Mostrar cada libro con sus opciones
        for book_id, info in sorted_book_items:
            # Asegurarse de que 'info' sea un diccionario con 'title' y 'author'
            if isinstance(info, dict) and 'title' in info and 'author' in info:
                 col1, col2, col3 = st.columns([3, 1.5, 1]) # Ajustar ratios si es necesario

                 with col1:
                     st.markdown(f"**{info['title']}** por *{info['author']}*")
                     # st.caption(f"ID: {book_id}") # Descomentar para ver el ID

                 with col2:
                     # Usar st.link_button para una navegación más clara a la página del usuario
                     st.link_button("🔗 Consultar Libro", f"/Usuario?book_id={book_id}")

                 with col3:
                     # Botón de eliminar con clave única para evitar problemas de estado
                     if st.button("🗑️ Eliminar", key=f"delete_{book_id}", help=f"Eliminar '{info['title']}'"):
                         # Considerar añadir un diálogo de confirmación aquí en una app real
                         with st.spinner(f"Eliminando '{info['title']}'..."):
                             if delete_book(book_id):
                                 st.success(f"Libro '{info['title']}' eliminado correctamente.")
                             else:
                                 st.error(f"Error al eliminar el libro '{info['title']}'.")
                         # Limpiar caché y re-ejecutar para actualizar la lista inmediatamente
                         # st.cache_data.clear()
                         # st.cache_resource.clear()
                         st.rerun()
            else:
                # Si la info de un libro no tiene el formato esperado
                st.warning(f"Registro de libro inválido encontrado para ID: {book_id}")


# --- Punto de entrada para ejecutar el panel ---
if __name__ == "__main__":
    admin_panel()