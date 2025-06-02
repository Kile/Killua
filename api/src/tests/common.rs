use std::{process::Command, sync::Once};
use zmq::{Context, Message, SocketType::ROUTER};

pub static INIT: Once = Once::new();

#[derive(serde::Deserialize)]
struct SimpleRequest {
    route: String,
}

#[allow(dead_code)]
#[derive(serde::Deserialize)]
struct Request {
    route: String,
    data: String,
}

/// Spins up a zmq server in the background
/// with the provided response.
pub fn test_zmq_server() {
    let context = Context::new();
    let responder = context.socket(ROUTER).unwrap();

    assert!(responder.set_rcvtimeo(5000).is_ok());
    assert!(responder.set_linger(0).is_ok());
    assert!(responder.bind("tcp://127.0.0.1:3210").is_ok());

    // Wait for a request in the background
    std::thread::spawn(move || {
        let poller = responder.as_poll_item(zmq::POLLIN);
        let items = &mut [poller];

        loop {
            if zmq::poll(items, -1).is_err() {
                continue; // Skip to the next iteration if polling fails
            }
            let mut identity = Message::new();
            responder.recv(&mut identity, 0).unwrap();
            let mut buffer = Message::new();
            responder.recv(&mut buffer, 0).unwrap();
            let mut msg = Message::new();
            responder.recv(&mut msg, 0).unwrap();

            let stripped: Vec<u8> = (msg.as_ref() as &[u8])[1..].to_vec();
            let str = String::from_utf8(stripped.clone()).unwrap();

            let request = serde_json::from_str::<SimpleRequest>(str.as_str())
                .expect("Failed to parse request");

            let respond_with = if request.route.as_str() == "update" {
                // If the request is an update, we need to parse the data as well
                let request = serde_json::from_str::<Request>(str.as_str())
                    .expect("Failed to parse request with data");

                let output = Command::new("sh")
                    .current_dir("..")
                    .arg("-c")
                    .arg(request.data)
                    .output()
                    .expect("Failed to run command");
                // Get the exit code
                let exit_code = output.status.code().unwrap_or(-1);
                // Get the output
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                let full_output = format!("{}{}", stdout, stderr);
                // Prepare the response
                format!("EXIT_CODE={}\nOUTPUT={}", exit_code, full_output)
            } else {
                match request.route
                .as_str()
            {
                "commands" => {
                    r#"{"CATEGORY": {"name": "category", "description": "", "emoji": {"normal": "a", "unicode": "b"}, "commands": []}}"#
                }
                "stats" => r#"{"guilds": 1, "shards": 1, "registered_users": 1, "last_restart": 1.0}"#,
                "vote" => r#"{"success": "true"}"#,
                "heartbeat" => r#"{"success": "true"}"#,
                _ => r#"{}"#,
            }.to_string()
            };
            let message = Message::from(respond_with.as_str());
            responder
                .send_multipart(vec![identity, message], 0)
                .unwrap();
        }
    });
}

/// Gets the API key from Rocket.toml
pub fn get_key() -> String {
    std::env::var("API_KEY").unwrap()
}
