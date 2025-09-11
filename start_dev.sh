#!/bin/bash
# Simple bash script alternative for starting development servers

echo "🚀 Starting Metal Albums Development Environment"
echo "============================================================"

# Check if Python dependencies are installed
echo "🔍 Checking Python dependencies..."
if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Check if frontend dependencies are installed
echo "🔍 Checking frontend dependencies..."
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    cd frontend && npm install && cd ..
fi

echo "✅ Dependencies ready"
echo ""

# Function to cleanup processes on exit
cleanup() {
    echo ""
    echo "🛑 Stopping development servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap for cleanup
trap cleanup SIGINT SIGTERM

# Start backend in test mode (API only)
echo "🚀 Starting FastAPI backend on http://127.0.0.1:8000"
python daily_orchestrator.py --test &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend development server
echo "🎨 Starting React frontend on http://localhost:3000"
cd frontend
BROWSER=none npm start &
FRONTEND_PID=$!
cd ..

# Wait for servers to be ready
sleep 5

# Show access information
echo ""
echo "============================================================"
echo "🎯 DEVELOPMENT SERVERS READY"
echo "============================================================"
echo "📊 Backend API:     http://127.0.0.1:8000"
echo "📊 API Docs:        http://127.0.0.1:8000/docs"
echo "🎨 Frontend:        http://localhost:3000"
echo "============================================================"
echo "💡 The frontend will proxy API requests to the backend"
echo "🔄 Both servers will auto-reload on file changes"
echo "⏹️  Press Ctrl+C to stop both servers"
echo "============================================================"
echo ""

# Keep script running and wait for processes
wait
