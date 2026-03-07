use log::{info, warn};
use zmq::{poll, Context, Message, DEALER, POLLIN, ROUTER};

#[repr(u8)]
#[derive(PartialEq)]
enum SocketType {
    Bot = 0_u8,
    Script = 1_u8,
}

impl SocketType {
    fn from_u8(value: u8) -> Option<SocketType> {
        match value {
            0 => Some(SocketType::Bot),
            1 => Some(SocketType::Script),
            _ => None,
        }
    }
}

/// Drain any stale messages sitting in a socket's receive buffer so that the
/// next `recv_multipart` call returns the response to the *current* request
/// rather than a leftover from a previously timed-out one.
fn drain_stale_messages(socket: &zmq::Socket, label: &str) {
    while let Ok(parts) = socket.recv_multipart(zmq::DONTWAIT) {
        warn!(
            "Drained stale message from {} ({} parts, {} bytes)",
            label,
            parts.len(),
            parts.iter().map(|p| p.len()).sum::<usize>()
        );
    }
}

/// Send an error response back to the API client so it doesn't hang waiting
/// for a reply that will never come.
fn send_error_to_api(api: &zmq::Socket, identity: Message, error_msg: &str) {
    let error_json = format!(r#"{{"error":"{}"}}"#, error_msg);
    if let Err(e) = api.send(identity, zmq::SNDMORE) {
        warn!("Failed to send error identity to API: {:?}", e);
        return;
    }
    if let Err(e) = api.send("", zmq::SNDMORE) {
        warn!("Failed to send error delimiter to API: {:?}", e);
        return;
    }
    if let Err(e) = api.send(error_json.as_bytes(), 0) {
        warn!("Failed to send error body to API: {:?}", e);
    }
}

fn main() {
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let api_address = std::env::var("ZMQ_API_ADDRESS").unwrap();
    let bot_address = std::env::var("ZMQ_BOT_ADDRESS").unwrap();
    let script_address = std::env::var("ZMQ_SCRIPT_ADDRESS").unwrap();

    info!("Starting device...");
    info!("Client address: {}", api_address);
    info!("Server address: {}", bot_address);
    info!("Script address: {}", script_address);

    let context = Context::new();
    let api = context.socket(ROUTER).unwrap();
    let bot = context.socket(DEALER).unwrap();
    let script = context.socket(DEALER).unwrap();
    api.set_identity("api-client".as_bytes()).unwrap();
    bot.set_identity("bot-client".as_bytes()).unwrap();
    script.set_identity("script-client".as_bytes()).unwrap();
    assert!(api.bind(&api_address).is_ok());
    assert!(bot.bind(&bot_address).is_ok());
    assert!(script.bind(&script_address).is_ok());

    let sockets = vec![&api, &bot, &script];
    for socket in &sockets {
        assert!(socket.set_rcvtimeo(5000).is_ok());
        assert!(socket.set_linger(0).is_ok());
        assert!(socket.set_sndtimeo(1000).is_ok());
    }

    let items = &mut [
        api.as_poll_item(POLLIN),
        bot.as_poll_item(POLLIN),
        script.as_poll_item(POLLIN),
    ];

    info!("Setup complete");
    loop {
        match poll(items, -1) {
            Ok(_) => {}
            Err(e) => {
                warn!("Polling failed: {:?}", e);
                continue; // Skip to the next iteration if polling fails
            }
        }

        // Drain stale responses from bot/script sockets that arrived after a
        // previous timeout. Without this the poll loop would spin (socket stays
        // readable) and the next request would receive a stale response.
        if items[1].is_readable() {
            drain_stale_messages(&bot, "bot");
        }
        if items[2].is_readable() {
            drain_stale_messages(&script, "script");
        }

        if items[0].is_readable() {
            let mut identity = Message::new();
            api.recv(&mut identity, 0).unwrap();

            let mut delimiter = Message::new();
            api.recv(&mut delimiter, 0).unwrap(); // This should be an empty frame

            let mut message = Message::new();
            api.recv(&mut message, 0).unwrap();

            let more = if api.get_rcvmore().unwrap() {
                zmq::SNDMORE
            } else {
                0
            };

            if let Some(&first_byte) = message.as_ref().first() {
                let remaining = &message.as_ref()[1..];
                let new_msg = zmq::Message::from(remaining);
                let socket_type =
                    SocketType::from_u8(first_byte).expect("Invalid first byte in message");

                let (socket, label) = if socket_type == SocketType::Bot {
                    (&bot, "bot")
                } else {
                    (&script, "script")
                };

                // Belt-and-suspenders: drain again right before we send, in case a
                // stale response arrived between the poll-level drain and now.
                drain_stale_messages(socket, label);

                socket.send(new_msg, more).unwrap();
                info!("Forwarded to {}", label);

                match socket.recv_multipart(0) {
                    Ok(reply_parts) => {
                        info!("Received response from {}", label);

                        api.send(identity, zmq::SNDMORE).unwrap();
                        api.send("", zmq::SNDMORE).unwrap();
                        for (i, part) in reply_parts.iter().enumerate() {
                            let flag = if i == reply_parts.len() - 1 {
                                0
                            } else {
                                zmq::SNDMORE
                            };
                            api.send(part, flag).unwrap();
                        }
                        info!("Forwarded response to API");
                    }
                    Err(e) => {
                        warn!("Timeout waiting for {} response: {:?}", label, e);
                        send_error_to_api(
                            &api,
                            identity,
                            &format!(
                                "Proxy timeout: {} did not respond within the timeout window",
                                label
                            ),
                        );
                    }
                }
            }
        }
    }
}
