#!/bin/bash

# College Counselor - Setup Script
# Installs all dependencies and prepares for deployment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        College Counselor - Setup Script                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Setup backend
echo -e "${YELLOW}Setting up backend...${NC}"
cd agents

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing backend dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

cd ..

# Setup frontend
echo -e "${YELLOW}Setting up frontend...${NC}"
cd frontend

echo "Installing frontend dependencies..."
npm install

cd ..

# Setup cloud function
echo -e "${YELLOW}Setting up cloud function...${NC}"
cd cloud_functions/profile_manager

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing cloud function dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

cd ../..

echo ""
echo -e "${GREEN}✓ Setup complete!${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set environment variables:"
echo "   export GCP_PROJECT_ID='your-project-id'"
echo "   export GEMINI_API_KEY='your-api-key'"
echo ""
echo "2. Run deployment:"
echo "   ./deploy.sh"
echo ""
echo "3. Or run locally:"
echo "   ./start_local.sh"
