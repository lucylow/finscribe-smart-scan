# PaddleOCR-VL Financial Document Analyzer - Streamlit Demo

This is the Phase 4 demonstration application for the hackathon project, showcasing the fine-tuned PaddleOCR-VL model's capabilities in processing financial documents.

## Features

- 📤 **Interactive Upload**: Upload and analyze financial documents in real-time
- ⚖️ **Side-by-Side Comparison**: Compare fine-tuned vs vanilla PaddleOCR models
- 📊 **Real Invoice Showcase**: Test on challenging real-world invoice samples
- 📈 **Performance Metrics**: View comprehensive benchmarks and improvements
- 🔧 **How It Works**: Technical deep-dive into the architecture

## Quick Start

### 1. Install Dependencies

```bash
pip install -r streamlit_demo/requirements.txt
```

### 2. Set Environment Variables (Optional)

```bash
# Model configuration
export MODEL_MODE=mock  # Options: mock, local, remote

# If using remote models
export PADDLEOCR_VLLM_URL=http://localhost:8001/v1
export ERNIE_VLLM_URL=http://localhost:8002/v1
```

### 3. Run the Application

```bash
streamlit run streamlit_demo/app.py
```

The application will open in your browser at `http://localhost:8501`

## Project Structure

```
streamlit_demo/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
├── models/
│   ├── __init__.py
│   ├── fine_tuned_pipeline.py     # Fine-tuned PaddleOCR-VL wrapper
│   └── vanilla_pipeline.py        # Vanilla PaddleOCR wrapper
└── utils/
    ├── __init__.py
    ├── visualizer.py              # Visualization utilities
    └── processor.py               # Processing and metrics utilities
```

## Configuration

### Model Modes

The demo supports three model modes:

1. **mock**: Uses mock/dummy models (for testing without GPU/models)
2. **local**: Uses locally loaded models
3. **remote**: Connects to remote vLLM servers

Set via environment variable: `MODEL_MODE=mock`

### Adding Sample Images

Place challenging invoice samples in:
```
streamlit_demo/assets/real_invoices/
```

Supported formats: `.jpg`, `.jpeg`, `.png`

## Demo Modes

### 📤 Interactive Upload
Upload any financial document and see real-time analysis with:
- Structured data extraction
- Invoice summary
- Validation details
- Visual annotations

### ⚖️ Side-by-Side Comparison
Compare fine-tuned model against vanilla PaddleOCR:
- Data quality comparison
- Performance metrics
- Accuracy analysis
- Visual extraction comparison

### 📊 Real Invoice Showcase
Test on challenging real-world cases:
- Blurry photos
- Dense tables
- Handwritten annotations
- Multi-language documents

### 📈 Performance Metrics
View comprehensive benchmarks:
- Field extraction accuracy
- Table recognition
- Processing speed
- Noise robustness

### 🔧 How It Works
Technical documentation:
- Architecture overview
- Fine-tuning process
- Deployment instructions

## Troubleshooting

### Models Not Loading

If you see "Model not loaded" errors:

1. Check that `MODEL_MODE` is set correctly
2. For `local` mode, ensure models are downloaded
3. For `remote` mode, verify vLLM servers are running
4. Check console logs for detailed error messages

### Import Errors

If you see import errors:

1. Ensure you're in the project root directory
2. Verify all dependencies are installed: `pip install -r streamlit_demo/requirements.txt`
3. Check that the `app/` directory is accessible (parent directory)

### Performance Issues

For slow processing:

1. Use `MODEL_MODE=mock` for faster demo without actual models
2. Reduce image resolution before upload
3. Check system resources (GPU/CPU/memory)

## Development

### Adding New Features

1. **New Demo Mode**: Add method to `FinancialDocumentDemo` class in `app.py`
2. **New Visualization**: Extend `DocumentVisualizer` in `utils/visualizer.py`
3. **New Metrics**: Add functions to `utils/processor.py`

### Testing

Test individual components:
```python
from models.fine_tuned_pipeline import FineTunedInvoiceAnalyzer
from utils.visualizer import DocumentVisualizer

# Test model loading
model = FineTunedInvoiceAnalyzer()

# Test visualization
visualizer = DocumentVisualizer()
```

## Deployment

### Local Development
```bash
streamlit run streamlit_demo/app.py
```

### Production (Hugging Face Spaces)
1. Push code to GitHub repository
2. Create new Space on Hugging Face
3. Connect repository
4. Set environment variables in Space settings
5. Enable automatic deployments

### Docker
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["streamlit", "run", "streamlit_demo/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## License

Part of the FinScribe Smart Scan hackathon project.

## Support

For issues or questions, please refer to the main project documentation or open an issue in the repository.
