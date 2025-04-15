#!/bin/bash
cd /home/site/wwwroot
pip install -r requirements.txt
mkdir -p .streamlit
mkdir -p data/vector_stores
streamlit run _📚_Usuario.py --server.port=8000 --server.address=0.0.0.0