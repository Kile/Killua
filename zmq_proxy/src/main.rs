use log::info;
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

fn main() {
    // set logging level to info
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

    let items = &mut [api.as_poll_item(POLLIN), bot.as_poll_item(POLLIN), script.as_poll_item(POLLIN)];

    info!("Setup complete");
    loop {
        match poll(items, -1)
        {
            Ok(_) => info!("Polling successful"),
            Err(e) => {
                info!("Polling failed: {:?}", e);
                continue; // Skip to the next iteration if polling fails
            }
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
                let socket_type = SocketType::from_u8(first_byte).expect("Invalid first byte in message");
        
                let socket = if socket_type == SocketType::Bot {
                    &bot
                } else {
                    &script
                };
        
                socket.send(new_msg, more).unwrap();
                info!("Forwarded to {}", if socket_type == SocketType::Bot { "bot" } else { "script" });
        
                match socket.recv_multipart(0) {
                    Ok(reply_parts) => {
                        info!("Received response: {:?}", reply_parts);
        
                        // Send back to the original client
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
                    },
                    Err(e) => {
                        info!("Timeout from {}: {:?}", if socket_type == SocketType::Bot { "bot" } else { "script" }, e);
                    }
                }
            }
        }
    }
}
