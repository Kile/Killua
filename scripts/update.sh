#!/bin/bash

# Check if --test is supplied
if [[ "$1" == "--test-pass" ]]; then
    echo "Test passed"
    exit 0
fi

# Check if --test-failed is supplied
if [[ "$1" == "--test-fail" ]]; then
    >&2 echo "Test failed"
    exit 1
fi

# Git pull
echo "Running git pull..."
git pull || { echo "git pull failed"; exit 1; }

# Docker compose pull
echo "Running docker compose pull..."
docker compose pull || { echo "docker compose pull failed"; exit 1; }

# Determine if --force was passed
FORCE_RECREATE=""
if [[ "$1" == "--force" ]]; then
    FORCE_RECREATE="--force-recreate"
fi

# Docker compose up
echo "Running docker compose up -d $FORCE_RECREATE..."
docker compose up -d $FORCE_RECREATE || { echo "docker compose up failed"; exit 1; }

echo "Deployment complete."
