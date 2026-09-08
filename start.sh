#!/bin/bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo -e "\033[0;36mStarting PDF Q&A...\033[0m"

# Kill stale processes
function kill_port {
    local PORT=$1
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo -e "\033[0;33mPort $PORT is in use. Killing stale processes...\033[0m"
        lsof -ti:$PORT | xargs kill -9
        sleep 2
    fi
}

kill_port 8001
kill_port 5174

if [ "$1" == "--install" ] || [ "$1" == "-i" ]; then
    echo -e "\033[0;36mInstalling Backend Dependencies...\033[0m"
    cd backend
    pip install -r requirements.txt
    cd ..

    echo -e "\033[0;36mInstalling Frontend Dependencies...\033[0m"
    cd frontend
    npm install
    cd ..
fi

echo -e "\033[0;36mChecking NLP dependencies...\033[0m"
python -c "import nltk; nltk.download('punkt_tab')"

# Start Backend
echo -e "\033[0;36mStarting Backend...\033[0m"
cd backend
python main.py &
BACKEND_PID=$!
cd ..

sleep 2

# Start Frontend
echo -e "\033[0;36mStarting Frontend...\033[0m"
cd frontend
npm run dev -- --port 5174 &
FRONTEND_PID=$!
cd ..

# Handle shutdown
function cleanup {
    echo -e "\033[0;33mShutting down...\033[0m"
    kill $BACKEND_PID
    kill $FRONTEND_PID
    exit 0
}
trap cleanup SIGINT SIGTERM

echo -e "\033[0;32mServices started! Press Ctrl+C to stop.\033[0m"
wait
