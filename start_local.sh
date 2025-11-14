#!/bin/bash

# College Counselor - Local Development Script
# Starts backend and frontend for local testing

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     College Counselor - Local Development                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check environment variables
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${YELLOW}Warning: GEMINI_API_KEY not set${NC}"
    echo "Set it with: export GEMINI_API_KEY='your-api-key'"
    echo ""
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $(jobs -p) 2>/dev/null
    exit
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${YELLOW}Starting backend agent...${NC}"
cd agents
source .venv/bin/activate
CORS_ALLOW_ORIGINS="*" adk web &
BACKEND_PID=$!
echo -e "${GREEN}✓ Backend started (PID: $BACKEND_PID)${NC}"
echo -e "${GREEN}  URL: http://localhost:8080${NC}"
cd ..

# Wait for backend to start
sleep 3

# Start frontend
echo -e "${YELLOW}Starting frontend...${NC}"
cd frontend

# Create .env for local development
cat > .env.local << EOF
VITE_API_URL=http://localhost:8080
EOF

npm run dev &
FRONTEND_PID=$!
echo -e "${GREEN}✓ Frontend started (PID: $FRONTEND_PID)${NC}"
echo -e "${GREEN}  URL: http://localhost:3000${NC}"
cd ..

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              Local Development Running                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Services:${NC}"
echo "  Backend:  http://localhost:8080"
echo "  Frontend: http://localhost:3000"
echo ""
echo -e "${YELLOW}Note:${NC} Profile upload/list/delete will not work locally"
echo "      (requires deployed cloud function)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Wait for processes
wait
