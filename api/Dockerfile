# Use an official Rust runtime as a parent image
FROM rust:1.78 AS base

ARG MYUID=1000
ARG MYGID=1000

# Set the working directory in the container
WORKDIR /app

COPY api/ api/

RUN mv api/Rocket.toml.template api/Rocket.toml

# This is mainly for reading the config.json
WORKDIR /app/api

# Runs in development and production on port 8000 (in the container)
EXPOSE 8000

FROM base AS prod

# Build the Rust application
RUN cargo build --release

# Create a user and group to run the application
RUN groupadd -g "${MYGID}" api \
  && useradd --create-home --no-log-init -u "${MYUID}" -g "${MYGID}" api
USER api

# Set the binary as the entrypoint
CMD ["./target/release/api"]

# run without release flag for development
FROM base AS dev

# Build the Rust application no cache
RUN cargo build

# Create a user and group to run the application
RUN groupadd -g "${MYGID}" api \
  && useradd --create-home --no-log-init -u "${MYUID}" -g "${MYGID}" api
USER api

# Set the binary as the entrypoint
CMD ["./target/debug/api"]

