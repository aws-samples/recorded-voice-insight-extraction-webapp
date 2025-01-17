FROM python:3.11-slim@sha256:ad5dadd957a398226996bc4846e522c39f2a77340b531b28aaab85b2d361210b

WORKDIR /app

# Create a non-root user and switch to it
RUN addgroup --system appgroup && adduser --system --group appuser

COPY requirements.txt .
RUN pip3 install -r requirements.txt --no-cache-dir

# Change ownership of the /app directory to the appuser
RUN chown -R appuser:appgroup /app
USER appuser

COPY . .

EXPOSE 8501
HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8501/_stcore/health"]
ENTRYPOINT ["streamlit", "run", "💡_Home.py", "--server.port=8501", "--server.address=0.0.0.0", "--logger.level=info", "--server.maxUploadSize=10280"]