FROM python:3.10-slim

RUN apt-get update && apt-get install -y libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY ocr_service/ ocr_service/
RUN pip install --upgrade pip
RUN pip install paddlepaddle paddleocr fastapi uvicorn[standard] aiofiles python-multipart

EXPOSE 8000
CMD ["uvicorn", "ocr_service.ocr_api:app", "--host", "0.0.0.0", "--port", "8000"]
