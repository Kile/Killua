FROM rust:1.87 AS base

ARG MYUID=1000
ARG MYGID=1000

COPY . .

FROM base AS prod

EXPOSE 5558

# Build the Rust application
RUN cargo build --release

# Create a user and group to run the application
RUN groupmod -g "${MYGID}" proxy && usermod -u "${MYUID}" -g "${MYGID}" proxy
USER proxy

# Set the binary as the entrypoint
CMD ["./target/release/zmq_proxy"]

# run without release flag for development
FROM base AS dev

# Build the Rust application
RUN cargo build

# Create a user and group to run the application
RUN groupmod -g "${MYGID}" proxy && usermod -u "${MYUID}" -g "${MYGID}" proxy
USER proxy

# Set the binary as the entrypoint
CMD ["./target/debug/zmq_proxy"]
