#!/bin/bash
echo "Uploading image to dockerhub"
echo "$DOCKER_PASSWORD" | docker login -u "$DOCKER_USERNAME" --password-stdin
docker push europython/epcon
