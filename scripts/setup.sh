#!/bin/bash
set -e

echo "==================================================="
echo "            AgentForge Setup Installer"
echo "==================================================="
echo "Checking dependencies..."

# Check python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed. Please install Python 3.11+."
    exit 1
else
    echo "[OK] Python 3 detected."
fi

# Check node
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed. Please install Node 18+."
    exit 1
else
    echo "[OK] Node.js detected."
fi

# Setup python venv in backend
echo ""
echo "Setting up Python virtual environment..."
cd "$(dirname "$0")/../backend"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
echo "Installing Backend dependencies..."
pip install -r requirements.txt
deactivate

# Setup npm in frontend
echo ""
echo "Installing Frontend NPM dependencies..."
cd "$(dirname "$0")/../frontend"
npm install

echo ""
echo "==================================================="
echo "Setup complete!"
echo "To run backend: cd backend && source venv/bin/activate && uvicorn app.main:app --reload"
echo "To run frontend: cd frontend && npm run dev"
echo "==================================================="
