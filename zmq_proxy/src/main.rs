use log::info;
use zmq::{poll, Context, Message, DEALER, POLLIN, ROUTER};

fn main() {
    // set logging level to info
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let client_address = std::env::var("ZMQ_CLIENT_ADDRESS").unwrap();
    let server_address = std::env::var("ZMQ_SERVER_ADDRESS").unwrap();

    info!("Starting device...");
    info!("Client address: {}", client_address);
    info!("Server address: {}", server_address);

    let context = Context::new();
    let frontend = context.socket(ROUTER).unwrap();
    let backend = context.socket(DEALER).unwrap();
    assert!(frontend.bind(&client_address).is_ok());
    assert!(backend.bind(&server_address).is_ok());

    let items = &mut [frontend.as_poll_item(POLLIN), backend.as_poll_item(POLLIN)];

    info!("Setup complete");
    loop {
        poll(items, -1).unwrap();
        if items[0].is_readable() {
            loop {
                let mut message = Message::new();
                frontend.recv(&mut message, 0).unwrap();
                // let message = backend.recv_msg(0).unwrap();
                let more = if frontend.get_rcvmore().unwrap() {
                    zmq::SNDMORE
                } else {
                    0
                };
                // backend.send(message, 0).unwrap();
                backend.send(message, more).unwrap();
                info!("Forwarded received frontend message to backend");
                if more == 0 {
                    break;
                };
            }
        }
        if items[1].is_readable() {
            loop {
                let mut message = Message::new();
                backend.recv(&mut message, 0).unwrap();
                let more = if backend.get_rcvmore().unwrap() {
                    zmq::SNDMORE
                } else {
                    0
                };
                frontend.send(message, more).unwrap();
                info!("Forwarded received backend message to frontend");
                if more == 0 {
                    break;
                }
            }
        }
    }
}
