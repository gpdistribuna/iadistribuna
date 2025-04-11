from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.prompts import PromptTemplate
import os

# Importar variables necesarias
from utils.book_processing import VECTOR_DIR

def load_vector_store(book_id: str) -> FAISS:
    """Carga un índice vectorial previamente guardado."""
    book_vector_dir = os.path.join(VECTOR_DIR, book_id)
    
    # Obtener API key desde variable de entorno
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("No se encontró la API key de OpenAI. Configura la variable de entorno OPENAI_API_KEY.")
    
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=openai_api_key)
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
    - Cita capítulos, secciones o páginas específicas cuando sea posible.
    - Proporciona una respuesta clara, concisa y directa.
    - Indica la página de donde sacaste la información siempre que sea posible.
    
    Respuesta:
    """
    
    PROMPT = PromptTemplate(
        template=template, 
        input_variables=["context", "question"]
    )
    
    # Obtener API key desde variable de entorno
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise ValueError("No se encontró la API key de OpenAI. Configura la variable de entorno OPENAI_API_KEY.")
    
    # Configurar el modelo de lenguaje con API key
    llm = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=openai_api_key)
    
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
    try:
        return qa_chain.run(question)
    except Exception as e:
        if "api_key" in str(e).lower():
            return "Error: No se pudo conectar con OpenAI. Por favor, verifica la configuración de la API key."
        else:
            return f"Error al procesar la pregunta: {str(e)}"