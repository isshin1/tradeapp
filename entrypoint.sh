#!/bin/sh
set -e


cleanup() {
    echo "🔄 Calling cleanup API before shutdown..."
    # Retry a few times in case app is still starting or shutting down
    for i in 1 2 3; do
        if curl -s -X GET http://127.0.0.1:8000/api/killswitch; then
            break
        fi
        sleep 1
    done
}


trap cleanup 15

# Start FastAPI (Uvicorn) in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &

pid="$!"

# Wait for the process to end
wait "$pid"
