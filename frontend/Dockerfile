FROM python:3.9-slim

WORKDIR /app

COPY * .
RUN pip3 install -r requirements.txt

EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT ["streamlit", "run", "💡_Home.py", "--server.port=8501", "--server.address=0.0.0.0", "--logger.level=info", "--server.maxUploadSize=1028"]