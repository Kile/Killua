# Use an official Rust runtime as a parent image
FROM rust:1.78 AS base

# Set the working directory in the container
WORKDIR /app

COPY api/ api/

# This is mainly for reading the config.json
WORKDIR /app/api

RUN mv Rocket.toml.example Rocket.toml

# Runs in development and production on port 8000 (in the container)
EXPOSE 8000

FROM base as prod

# Build the Rust application
RUN cargo build --release

# Set the binary as the entrypoint
CMD ["./target/release/api"]

# run without release flag for development
FROM base as dev

# Build the Rust application no cache
RUN cargo build

# Set the binary as the entrypoint
CMD ["./target/debug/api"]

