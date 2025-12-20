# Quick Start Guide - Streamlit Demo

Get the demo running in 3 simple steps!

## Step 1: Install Dependencies

```bash
pip install -r streamlit_demo/requirements.txt
```

**Note**: For PDF support, you may also need system dependencies:
- **macOS**: `brew install poppler`
- **Ubuntu/Debian**: `sudo apt-get install poppler-utils`
- **Windows**: Download poppler binaries and add to PATH

## Step 2: Run the Demo

### Option A: Using the run script
```bash
./streamlit_demo/run.sh
```

### Option B: Using streamlit directly
```bash
streamlit run streamlit_demo/app.py
```

## Step 3: Open Your Browser

The demo will automatically open at `http://localhost:8501`

If it doesn't open automatically, navigate to that URL manually.

## Using Mock Mode (Default)

By default, the demo runs in **mock mode**, which uses simulated data. This allows you to:

- ✅ Test the UI and features immediately
- ✅ See how the demo works without GPU/models
- ✅ Develop and test new features quickly

To use real models, set the environment variable:
```bash
export MODEL_MODE=local  # or 'remote'
```

## Troubleshooting

### "Module not found" errors
- Make sure you're in the project root directory
- Verify dependencies: `pip list | grep streamlit`

### Models not loading
- Check `MODEL_MODE` environment variable
- For `remote` mode, ensure vLLM servers are running
- Check console for detailed error messages

### PDF upload fails
- Install system dependencies (poppler)
- Verify pdf2image is installed: `pip show pdf2image`

## Next Steps

- 📤 Try uploading an invoice in "Interactive Upload" mode
- ⚖️ Compare models in "Side-by-Side Comparison"
- 📊 Explore performance metrics
- 🔧 Read the technical docs in "How It Works"

Happy demoing! 🎉
