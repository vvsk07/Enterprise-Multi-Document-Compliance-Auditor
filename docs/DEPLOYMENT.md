# DEPLOYMENT GUIDE

## Local Execution (Windows CPU)

1. **Environment Setup**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   ```

2. **Run Application**:
   ```powershell
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

3. **Run Streamlit Dashboard**:
   ```powershell
   streamlit run frontend/streamlit_app.py
   ```

## Docker Deployment

1. **Build Container**:
   ```bash
   docker build -t enterprise-compliance-auditor .
   ```

2. **Run Container Compose**:
   ```bash
   docker-compose up -d
   ```

3. **Health Check**:
   ```bash
   curl http://localhost:8000/health/live
   ```
