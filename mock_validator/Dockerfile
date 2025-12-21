FROM python:3.10-slim
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app
COPY app.py /app/app.py
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi uvicorn[standard] python-dateutil pydantic
EXPOSE 8100
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8100"]


