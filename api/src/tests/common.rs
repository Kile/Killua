use std::sync::Once;
use zmq::{Context, Message, REP};

pub static INIT: Once = Once::new();

#[derive(serde::Deserialize)]
struct Request {
    route: String,
}

/// Spins up a zmq server in the background
/// with the provided response.
pub fn test_zmq_server() {
    let context = Context::new();
    let responder = context.socket(REP).unwrap();

    assert!(responder.set_rcvtimeo(5000).is_ok());
    assert!(responder.set_linger(0).is_ok());
    assert!(responder.bind("tcp://127.0.0.1:3210").is_ok());

    // Wait for a request in the background
    std::thread::spawn(move || loop {
        let mut msg = Message::new();
        responder.recv(&mut msg, 0).unwrap();
        let respond_with = match serde_json::from_str::<Request>(msg.as_str().unwrap())
            .unwrap()
            .route
            .as_str()
        {
            "commands" => {
                r#"{"CATEGORY": {"name": "category", "description": "", "emoji": {"normal": "a", "unicode": "b"}, "commands": []}}"#
            }
            "stats" => r#"{"guilds": 1, "shards": 1, "registered_users": 1, "last_restart": 1.0}"#,
            "vote" => r#"{"success": "true"}"#,
            "heartbeat" => r#"{"success": "true"}"#,
            _ => r#"{}"#,
        };
        let message = Message::from(respond_with);
        responder.send(message, 0).unwrap();
    });
}

/// Gets the API key from Rocket.toml
pub fn get_key() -> String {
    std::env::var("API_KEY").unwrap()
}
