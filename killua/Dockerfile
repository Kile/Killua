# Use an official Python runtime as a parent image
FROM python:3.9-slim AS base

ARG MYUID=1000
ARG MYGID=1000

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY killua/ killua/

# This is kinda dumb but helps keep things defined in one place
COPY api/Rocket.toml api/Rocket.toml

# Copy requirements.txt, hugs.json and config.json which are needed for the bot
COPY requirements.txt .
# Copy config.json .
COPY hugs.json .
# Copy docker-compose.yml to know which port the API runs on publicly
COPY docker-compose.yaml .

# Git needs to be installed for pip
RUN apt-get update && apt-get install -y git

# Install C++ cause a dependency needs it
RUN apt-get install -y g++

# Clean up the cache
RUN apt-get clean

# Upgrade pip
RUN pip3 install --no-cache-dir --upgrade pip

# Install any needed packages specified in requirements.txt
RUN pip3 install --no-cache-dir -r requirements.txt

FROM base AS dev
# Create a user and group to run the application
RUN groupadd -g "${MYGID}" python \
&& useradd --create-home --no-log-init -u "${MYUID}" -g "${MYGID}" python
USER python
CMD ["python3", "-m", "killua", "--development", "--docker"]

FROM base AS prod
# Create a user and group to run the application
RUN groupadd -g "${MYGID}" python \
&& useradd --create-home --no-log-init -u "${MYUID}" -g "${MYGID}" python
USER python
CMD ["python3", "-m", "killua", "--docker", "--force-local"]