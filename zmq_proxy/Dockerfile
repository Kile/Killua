FROM rust:1.78 as base

COPY . .

FROM base as prod

# Build the Rust application
RUN cargo build --release

# Set the binary as the entrypoint
CMD ["./target/release/zmq_proxy"]

# run without release flag for development
FROM base as dev

# Build the Rust application no cache
RUN cargo build

# Set the binary as the entrypoint
CMD ["./target/debug/zmq_proxy"]