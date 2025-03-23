
1️⃣ Build the Docker Image
docker build -t flask-news-ai .
2️⃣ Run the Container
docker run -p 5000:5000 --env-file=config.env flask-news-ai

3️⃣ Upload to Docker Hub
docker tag flask-news-ai your_dockerhub_username/flask-news-ai
docker push your_dockerhub_username/flask-news-ai


1️⃣ Stop and Remove a Running Container
docker stop flask-news-ai  # Stop the container
docker rm flask-news-ai  # Remove the container

2️⃣ Remove a Docker Image
docker rmi flask-news-ai

3️⃣ Remove All Stopped Containers
docker container prune -f
