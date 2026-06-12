# Contributing to AgentForge

Thank you for choosing to help improve AgentForge! To maintain high code quality, please adhere to the following guidelines.

---

## 1. Local Environment Setup

### 1.1 Backend Setup
Navigate to the `backend` folder:
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

Launch the local server in development mode:
```bash
uvicorn app.main:app --reload --port 8000
```

### 1.2 Frontend Setup
Navigate to the `frontend` folder:
```bash
cd frontend
npm install
npm run dev
```

---

## 2. Coding Guidelines & Linting

We enforce clean architectures and strict type definitions:
- **Python**: Follow PEP 8 style patterns. Ensure all functions have clear type hints. Run tests locally before opening a pull request:
  ```bash
  $env:PYTHONPATH="."; .\venv\Scripts\pytest
  ```
- **TypeScript**: Use strict type definitions. Do not bypass checks with `any`.

---

## 3. Pull Request Cycle

1. **Create a Branch**: Create a feature branch off of `main` (e.g. `feature/parallel-workflows`).
2. **Commit Messages**: Write semantic, concise commit logs (e.g. `feat: add parallel asyncio steps to workflow execution`).
3. **Verify Checks**: Make sure unit and integration tests are passing.
4. **Open Review**: Target your PR to the `main` branch. Provide a detailed summary description of what changes are introduced.
