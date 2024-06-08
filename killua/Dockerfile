# Use an official Python runtime as a parent image
FROM python:3.9-slim AS base

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY killua/ killua/

# This is kinda dumb but helps keep things defined in one place
COPY api/Rocket.toml api/Rocket.toml

# Copy requirements.txt, hugs.json and config.json which are needed for the bot
COPY requirements.txt .
COPY config.json .
COPY hugs.json .

# Git needs to be installed for pip
RUN apt-get update && apt-get install -y git

# Install C++ cause a dependency needs it
RUN apt-get install -y g++

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

FROM base AS dev
CMD ["python3", "-m", "killua", "--development"]

FROM base as prod
CMD ["python3", "-m", "killua"]