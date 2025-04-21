# -----------------------------------------------------------------------------
# Dockerfile para la aplicación Streamlit de Consulta de Libros
# -----------------------------------------------------------------------------

# Paso 1: Usar una imagen base oficial de Python.
# 'slim' es una versión más ligera, buena para producción.
# Asegúrate de que la versión de Python sea compatible con tus dependencias (3.10 es una buena opción).
FROM python:3.10-slim

# Paso 2: Establecer el directorio de trabajo dentro del contenedor.
# Todos los comandos siguientes se ejecutarán desde /app.
WORKDIR /app

# Paso 3: Copiar el archivo de requisitos PRIMERO.
# Esto aprovecha el caché de capas de Docker. Si requirements.txt no cambia,
# Docker no reinstalará las dependencias en futuras construcciones, acelerando el proceso.
COPY requirements.txt ./requirements.txt

# Paso 4: Instalar las dependencias listadas en requirements.txt.
# --no-cache-dir reduce el tamaño final de la imagen al no guardar el caché de pip.
# --upgrade pip asegura que se use una versión reciente de pip.
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Paso 5: Copiar TODO el resto del código de la aplicación al directorio de trabajo.
# Esto incluye tus scripts .py (Home.py, _*.py), la carpeta utils/,
# la carpeta .streamlit/ si contiene archivos como style.css, etc.
COPY . .

# Paso 6: Exponer el puerto en el que se ejecutará Streamlit.
# El puerto por defecto de Streamlit es 8501. Azure App Service también lo espera si se configura.
EXPOSE 8501

# Paso 7: El comando para ejecutar la aplicación cuando el contenedor se inicie.
# - Ejecuta Streamlit usando 'streamlit run'.
# - Apunta a tu script principal 'Home.py'.
# - '--server.port=8501' asegura que use el puerto expuesto.
# - '--server.address=0.0.0.0' es crucial para que la aplicación sea accesible
#   desde fuera del contenedor dentro de la red de Docker/App Service.
CMD ["streamlit", "run", "Home.py", "--server.port=8501", "--server.address=0.0.0.0"]

# -----------------------------------------------------------------------------