FROM python:3.10-slim
WORKDIR /app
COPY frontend/ /app/frontend/
RUN pip install --no-cache-dir streamlit requests pillow
EXPOSE 8501
CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]

