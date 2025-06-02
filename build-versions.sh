#!/bin/bash

# Ensure script stops on first error
set -e

# Get the GitHub username from environment or prompt
GITHUB_USERNAME=${GITHUB_USERNAME:-$(git config --get user.name)}

if [ -z "$GITHUB_USERNAME" ]; then
    echo "Please set GITHUB_USERNAME environment variable"
    exit 1
fi

# Build v1 (original version)
echo "Building v1..."
docker build --build-arg VERSION=v1 -t ghcr.io/$GITHUB_USERNAME/app:v1 .

# Build v2 (enhanced feedback version)
echo "Building v2..."
docker build --build-arg VERSION=v2 -t ghcr.io/$GITHUB_USERNAME/app:v2 .

# Push images if requested
if [ "$1" = "--push" ]; then
    echo "Pushing v1..."
    docker push ghcr.io/$GITHUB_USERNAME/app:v1
    
    echo "Pushing v2..."
    docker push ghcr.io/$GITHUB_USERNAME/app:v2
fi

echo "Build complete!" 