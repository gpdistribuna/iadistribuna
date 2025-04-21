# utils/book_processing.py

import os
import json
import hashlib
import PyPDF2 # Para procesar PDFs
import shutil # Útil para operaciones de archivos/directorios
from typing import List, Dict, Any
import tempfile # Para crear directorios temporales seguros
import streamlit as st # Para mostrar mensajes de error en la UI

# Componentes de Langchain
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Utilidades de Azure Blob Storage (asegúrate de que estas funciones existan y funcionen)
from utils.azure_storage import (
    save_json_to_blob,
    load_json_from_blob,
    upload_blob,
    delete_blob,
    list_blobs,
    # blob_exists # Importar si se necesita verificar existencia de blobs individuales
)

# --- Constantes Configurables ---
# Nombre del blob donde se guarda el JSON con la info de los libros
BOOK_INFO_BLOB_NAME = "metadata/books_info.json"
# Prefijo en el blob storage donde se guardan los índices vectoriales
VECTOR_STORE_BLOB_PREFIX = "vector_stores"

# --- Funciones Principales ---

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extrae el texto completo de un archivo PDF.
    Maneja PDFs encriptados (con contraseña vacía) y errores de lectura.
    Lanza excepciones si el archivo no se encuentra o no se puede procesar.
    """
    text = ""
    print(f"[Debug] Intentando abrir PDF: {pdf_path}")
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            # Intentar desencriptar si es necesario
            if pdf_reader.is_encrypted:
                print(f"[Advertencia] PDF {os.path.basename(pdf_path)} está encriptado. Intentando desencriptar...")
                try:
                    if pdf_reader.decrypt('') == 0: # 0 indica fallo al desencriptar
                         raise ValueError("Contraseña incorrecta o fallo al desencriptar.")
                    print("[Debug] PDF desencriptado con éxito.")
                except Exception as decrypt_err:
                     print(f"ERROR: No se pudo desencriptar el PDF {os.path.basename(pdf_path)}: {decrypt_err}")
                     raise ValueError(f"El archivo PDF '{os.path.basename(pdf_path)}' está encriptado y no se pudo abrir.")

            # Extraer texto página por página
            num_pages = len(pdf_reader.pages)
            print(f"[Debug] Extrayendo texto de {num_pages} páginas...")
            for page_num in range(num_pages):
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text: # Añadir solo si se extrajo algo
                        text += page_text + "\n" # Separador entre páginas
                except Exception as page_err:
                    print(f"[Advertencia] No se pudo extraer texto de la página {page_num + 1} de {os.path.basename(pdf_path)}: {page_err}")
            print(f"[Debug] Extracción de texto completada. Longitud total: {len(text)}")
            if not text.strip():
                 print(f"[Advertencia] No se extrajo texto del PDF: {os.path.basename(pdf_path)}")
                 # Considerar lanzar un error si no se extrajo nada útil

    except FileNotFoundError:
        print(f"ERROR: Archivo PDF no encontrado en {pdf_path}")
        raise # Re-lanzar la excepción original
    except Exception as e:
        print(f"ERROR crítico al leer o procesar el PDF {pdf_path}: {str(e)}")
        raise RuntimeError(f"Fallo al leer o extraer texto del PDF: {str(e)}") from e
    return text

def split_text_into_chunks(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[str]:
    """
    Divide el texto en fragmentos (chunks) usando RecursiveCharacterTextSplitter.
    Filtra chunks vacíos o muy pequeños. Lanza excepción en caso de error.
    """
    if not text or not text.strip():
        print("[Advertencia] Se intentó dividir texto vacío.")
        return []
    print(f"[Debug] Dividiendo texto (longitud {len(text)}) en chunks. Tamaño={chunk_size}, Solapamiento={chunk_overlap}")
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False, # Usar separadores estándar
        )
        chunks = text_splitter.split_text(text)
        # Filtrar chunks potencialmente inútiles
        min_chunk_len = 10 # Definir longitud mínima útil
        original_chunk_count = len(chunks)
        chunks = [chunk for chunk in chunks if len(chunk.strip()) >= min_chunk_len]
        filtered_count = len(chunks)
        print(f"[Debug] Texto dividido en {original_chunk_count} chunks iniciales, {filtered_count} chunks útiles (longitud >= {min_chunk_len}).")
        return chunks
    except Exception as e:
        print(f"ERROR al dividir texto en chunks: {str(e)}")
        raise RuntimeError(f"Fallo al dividir el texto: {str(e)}") from e

def create_vector_store(chunks: List[str], book_id: str) -> str:
    """
    Crea un índice vectorial FAISS, lo guarda localmente de forma temporal
    y lo sube a Azure Blob Storage. Lanza una excepción si falla.
    Devuelve el prefijo de la ruta en Azure si tiene éxito.
    """
    print(f"[Debug] Iniciando create_vector_store para book_id: {book_id}")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("ERROR: Variable de entorno OPENAI_API_KEY no encontrada.")
        raise ValueError("OpenAI API key no encontrada. No se puede crear el vector store.")

    # Inicializar embeddings (asegúrate de que el modelo sea correcto)
    try:
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large", # Revisa si este es el modelo deseado/disponible
            openai_api_key=openai_api_key
        )
        print("[Debug] Embeddings de OpenAI inicializados.")
    except Exception as e:
         print(f"ERROR al inicializar OpenAI Embeddings: {str(e)}")
         raise RuntimeError(f"Fallo al inicializar OpenAI Embeddings: {str(e)}") from e

    vector_store = None # Inicializar a None
    try:
        print(f"[Debug] Intentando crear índice FAISS con {len(chunks)} chunks.")
        if not chunks:
             print("ERROR: No se puede crear índice FAISS desde una lista de chunks vacía.")
             raise ValueError("No se pueden crear vectores desde chunks de texto vacíos o filtrados.")
        # --- Creación del vector store ---
        vector_store = FAISS.from_texts(texts=chunks, embedding=embeddings)
        print("[Debug] Índice FAISS creado en memoria exitosamente.")
    except Exception as e:
        print(f"ERROR al crear índice FAISS desde textos: {str(e)}")
        raise RuntimeError(f"Fallo al crear el índice FAISS (verificar API Key, cuotas, chunks): {str(e)}") from e

    # --- Guardado local temporal y subida a Azure ---
    try:
        with tempfile.TemporaryDirectory(prefix=f"faiss_temp_{book_id}_") as temp_dir:
            book_vector_dir = os.path.join(temp_dir, "faiss_index") # Usar subcarpeta dentro del temp dir
            os.makedirs(book_vector_dir, exist_ok=True)

            print(f"[Debug] Intentando guardar índice FAISS localmente en: {book_vector_dir}")
            vector_store.save_local(folder_path=book_vector_dir) # Guardar en la subcarpeta
            print("[Debug] Índice FAISS guardado localmente con éxito.")

            # Definir nombres de blobs y rutas locales
            vector_store_prefix = f"{VECTOR_STORE_BLOB_PREFIX}/{book_id}"
            faiss_blob_name = f"{vector_store_prefix}/index.faiss"
            pkl_blob_name = f"{vector_store_prefix}/index.pkl"
            local_faiss_file = os.path.join(book_vector_dir, "index.faiss")
            local_pkl_file = os.path.join(book_vector_dir, "index.pkl")

            print(f"[Debug] Verificando archivos locales antes de subir: FAISS={os.path.exists(local_faiss_file)}, PKL={os.path.exists(local_pkl_file)}")
            if not os.path.exists(local_faiss_file) or not os.path.exists(local_pkl_file):
                 raise RuntimeError("Fallo crítico: los archivos index.faiss o index.pkl no se generaron correctamente en el directorio temporal.")

            # Subir archivos
            upload_success_faiss = False
            upload_success_pkl = False

            print(f"[Debug] Subiendo {local_faiss_file} a Azure: {faiss_blob_name}")
            if upload_blob(local_faiss_file, faiss_blob_name):
                print(f"[Debug] Subida de index.faiss a Azure exitosa.")
                upload_success_faiss = True
            else:
                print(f"ERROR al subir index.faiss a Azure.")

            print(f"[Debug] Subiendo {local_pkl_file} a Azure: {pkl_blob_name}")
            if upload_blob(local_pkl_file, pkl_blob_name):
               print(f"[Debug] Subida de index.pkl a Azure exitosa.")
               upload_success_pkl = True
            else:
               print(f"ERROR al subir index.pkl a Azure.")

            # Verificar que ambos archivos esenciales se subieron
            if not (upload_success_faiss and upload_success_pkl):
                 # Intentar limpiar blobs parcialmente subidos podría ser complejo.
                 # Por ahora, simplemente lanzar el error.
                 raise RuntimeError("Fallo al subir uno o más archivos del vector store (.faiss, .pkl) a Azure Blob Storage.")

            print(f"[Debug] Subida completa a Azure para {vector_store_prefix}")
            return vector_store_prefix # Devolver prefijo de Azure como indicador de éxito

    except Exception as e:
        # Capturar errores de guardado local o subida
        print(f"ERROR durante el guardado local o la subida a Azure: {str(e)}")
        raise RuntimeError(f"Fallo durante el guardado local o subida a Azure: {str(e)}") from e


def process_book(pdf_path: str, title: str, author: str) -> str | None:
    """
    Procesa un libro PDF completo: extrae texto, crea vectores y guarda la información.
    Devuelve el book_id si tiene éxito, None si falla.
    Maneja excepciones internas y muestra errores en Streamlit.
    """
    book_id = None # Inicializar book_id
    try:
        print(f"[Debug] Iniciando procesamiento del libro: Título='{title}', Autor='{author}'")
        # Generar ID único para el libro
        # Usar título y autor es simple, pero puede haber colisiones si se repiten.
        # Añadir algo más único si es necesario, pero mantenerlo determinista.
        book_id = hashlib.md5((title.strip() + author.strip()).encode('utf-8')).hexdigest()
        print(f"[Debug] Generado book_id: {book_id}")

        # 1. Extraer texto del PDF
        print("[Debug] Extrayendo texto del PDF...")
        text = extract_text_from_pdf(pdf_path)
        print(f"[Debug] Longitud del texto extraído: {len(text)}")
        if not text or len(text.strip()) < 50: # Chequeo de contenido mínimo
            raise ValueError("Fallo al extraer texto significativo del PDF o el PDF está vacío/corrupto.")

        # 2. Dividir texto en chunks
        print("[Debug] Dividiendo texto en chunks...")
        chunks = split_text_into_chunks(text) # Usar parámetros por defecto o personalizarlos
        print(f"[Debug] Dividido en {len(chunks)} chunks.")
        if not chunks:
             raise ValueError("La división del texto resultó en cero chunks útiles.")

        # 3. Crear y subir vector store (lanza excepción si falla)
        print("[Debug] Creando vector store...")
        create_vector_store(chunks, book_id) # Llama a la función que ahora sube a Azure
        print(f"[Debug] Vector store creado y subido a Azure para book_id: {book_id}")

        # 4. Guardar/Actualizar información del libro en Azure
        print("[Debug] Guardando información del libro en Azure...")
        book_info = get_book_info() # Cargar estado actual
        book_info[book_id] = {"title": title, "author": author}
        if not save_book_info(book_info):
             # Considerar esto un error crítico, ya que la app depende de este JSON
             print(f"ERROR CRÍTICO: Fallo al guardar la info del libro {book_id} en {BOOK_INFO_BLOB_NAME}.")
             raise RuntimeError(f"Fallo al guardar la información del libro '{title}' en Azure.")
        else:
             print("[Debug] Información del libro guardada/actualizada con éxito en Azure.")

        print(f"[Debug] Procesamiento del libro completado con éxito para book_id: {book_id}")
        return book_id # Éxito

    except Exception as e:
         # Capturar cualquier excepción durante todo el proceso
         error_message = f"Error al procesar el libro '{title}': {str(e)}"
         print(f"ERROR Completo en process_book: {error_message}") # Log detallado en servidor
         # Mostrar el error en la interfaz de Streamlit
         st.error(error_message)
         # Aquí podrías añadir lógica de limpieza si algo quedó a medias (ej. info guardada pero vector no)
         # pero puede ser complejo. Por ahora, solo indicamos el fallo.
         return None # Indicar fallo devolviendo None


# --- Funciones de Gestión de Metadatos (Interactúan con Azure) ---

#@st.cache_data(ttl=600) # Considerar cachear para reducir lecturas de Azure
def get_book_info() -> Dict[str, Any]:
    """Carga la información (metadatos) de los libros desde Azure Blob Storage."""
    print(f"[Debug] Cargando info de libros desde Azure blob: {BOOK_INFO_BLOB_NAME}")
    # load_json_from_blob debería devolver {} si el blob no existe o hay error
    data = load_json_from_blob(BOOK_INFO_BLOB_NAME)
    if not isinstance(data, dict):
        print(f"[ERROR] La data cargada de {BOOK_INFO_BLOB_NAME} no es un diccionario. Devolviendo diccionario vacío.")
        return {}
    print(f"[Debug] Info de libros cargada. Claves: {list(data.keys())}")
    return data

def save_book_info(book_info: Dict[str, Any]) -> bool:
    """Guarda la información (metadatos) de los libros en Azure Blob Storage."""
    print(f"[Debug] Guardando info de libros en Azure blob: {BOOK_INFO_BLOB_NAME}")
    success = save_json_to_blob(book_info, BOOK_INFO_BLOB_NAME)
    print(f"[Debug] Resultado de guardar info de libros: {success}")
    return success

def delete_book(book_id: str) -> bool:
    """
    Elimina un libro del sistema: su información de metadatos y
    todos los blobs de su vector store en Azure.
    """
    print(f"[Debug] Intentando eliminar libro con ID: {book_id}")
    success_overall = False
    try:
        book_info = get_book_info()

        if book_id not in book_info:
            print(f"[Advertencia] Intento de eliminar libro no existente en metadatos: {book_id}")
            # Aún así, intentar eliminar los blobs por si quedaron huérfanos
        else:
             # Eliminar la entrada de la información del libro primero lógicamente
            print(f"[Debug] Eliminando entrada de metadatos para: {book_id}")
            del book_info[book_id]
            if not save_book_info(book_info):
                 # Si falla guardar el JSON sin la entrada, es un problema grave.
                 print(f"[ERROR CRÍTICO] Fallo al guardar book_info después de eliminar la entrada para {book_id}. Reintentar o revisar permisos.")
                 # No continuar con la eliminación de blobs si no se pudo actualizar el índice
                 st.error(f"Error crítico al actualizar la lista de libros después de intentar eliminar '{book_id}'. No se eliminaron los datos asociados.")
                 return False
            else:
                 print(f"[Debug] Entrada de metadatos eliminada y archivo de info actualizado en Azure.")
                 success_overall = True # Marcamos éxito parcial (metadatos eliminados)


        # Eliminar blobs del vector store asociados al libro (incluso si no estaba en metadatos)
        vector_store_prefix_to_delete = f"{VECTOR_STORE_BLOB_PREFIX}/{book_id}/"
        print(f"[Debug] Buscando blobs para eliminar con prefijo: {vector_store_prefix_to_delete}")
        blobs_to_delete = list_blobs(prefix=vector_store_prefix_to_delete)

        if not blobs_to_delete:
             print(f"[Info] No se encontraron blobs de vector store para eliminar para book_id: {book_id}")
             # Si los metadatos se eliminaron bien, consideramos éxito total aquí
        else:
             print(f"[Debug] Encontrados blobs para eliminar: {blobs_to_delete}")
             delete_success_count = 0
             for blob_name in blobs_to_delete:
                 print(f"[Debug] Eliminando blob: {blob_name}")
                 if delete_blob(blob_name):
                     print(f"[Debug] Blob eliminado con éxito: {blob_name}")
                     delete_success_count += 1
                 else:
                     # Error al eliminar un blob específico
                     print(f"[ERROR] Fallo al eliminar blob: {blob_name}. Continuando con los demás...")
                     success_overall = False # Marcar que hubo algún fallo

             if delete_success_count == len(blobs_to_delete):
                 print(f"[Debug] Todos los {len(blobs_to_delete)} blobs del vector store eliminados con éxito.")
             else:
                 print(f"[Advertencia] Se eliminaron {delete_success_count} de {len(blobs_to_delete)} blobs del vector store.")
                 success_overall = False # Hubo fallos en la eliminación de blobs

        if success_overall:
            print(f"[Debug] Proceso de eliminación del libro completado (con posibles advertencias menores si blobs fallaron) para book_id: {book_id}")
        else:
            print(f"[ERROR] El proceso de eliminación del libro {book_id} encontró errores.")
            st.error(f"Se encontraron problemas al eliminar todos los datos asociados al libro ID {book_id}. Revise los logs.")


        return success_overall # Devuelve True solo si la info se actualizó y todos los blobs se borraron (o no existían)

    except Exception as e:
        # Capturar cualquier otro error inesperado
        error_msg_delete = f"Error inesperado durante la eliminación del libro {book_id}: {str(e)}"
        print(f"ERROR: {error_msg_delete}")
        st.error(error_msg_delete)
        return False

# Función auxiliar (puede no ser necesaria si la UI siempre selecciona explícitamente)
def get_default_book_id() -> str | None:
    """Obtiene el ID del primer libro en la lista, si existe."""
    book_info = get_book_info()
    if book_info:
        # Devolver la primera clave encontrada (el orden puede no estar garantizado)
        try:
            return next(iter(book_info))
        except StopIteration:
            return None
    return None

# --- Fin del archivo utils/book_processing.py ---