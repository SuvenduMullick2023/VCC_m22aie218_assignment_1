#!/bin/bash

# Set environment variables
export CONTAINER_NAME="flask-news-ai"
export IMAGE_NAME="flask-news-ai"
export HOST_PORT=5000
export CONTAINER_PORT=5000

echo "🚀 Building Docker image..."
docker build -t $IMAGE_NAME .

# Check if a container with the same name is already running
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "⚠️ Stopping existing container..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi

echo "🐳 Running container..."
docker run -d --name $CONTAINER_NAME -p $HOST_PORT:$CONTAINER_PORT --env-file=config.env $IMAGE_NAME

echo "✅ Container is running. Access it at: http://localhost:$HOST_PORT"
