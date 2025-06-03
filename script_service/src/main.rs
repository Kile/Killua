use log::info;
use serde::Deserialize;
use serde_json::from_str;
use std::process::Command;
use zmq::{Context, DONTWAIT, Message, POLLIN, ROUTER, poll};

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
struct Instruction<'a> {
    route: &'a str,
    data: &'a str,
}

fn main() {
    // set logging level to info
    env_logger::Builder::from_env(env_logger::Env::default().default_filter_or("info")).init();

    let context = Context::new();
    let responder = context.socket(ROUTER).unwrap();
    let poller = responder.as_poll_item(POLLIN);

    assert!(responder.connect("tcp://127.0.0.1:5558").is_ok());

    info!("Starting device...");

    let items = &mut [poller];

    // Wait for a request
    loop {
        // Poll for incoming messages
        info!("Waiting for messages...");
        if poll(items, -1).is_err() {
            info!("Polling failed... Retrying...");
            continue; // Skip to the next iteration if polling fails
        }
        if !items[0].is_readable() {
            info!("No messages received, continuing to wait...");
            continue; // Skip to the next iteration if no messages are readable
        }
        info!("Message received, processing...");
        let mut identity = Message::new();
        responder.recv(&mut identity, DONTWAIT).unwrap();
        let str = responder.recv_string(0).unwrap();
        info!("Received string: {:?}", str);
        let str_unwrapped = str.unwrap();
        let parsed = from_str::<Instruction>(&str_unwrapped).unwrap();
        info!("Received message: {}", parsed.data);
        // Execute the command
        let output = Command::new("sh")
            .current_dir("..")
            .arg("-c")
            .arg(parsed.data)
            .output()
            .expect("Failed to run command");
        // Get the exit code
        let exit_code = output.status.code().unwrap_or(-1);
        // Get the output
        let stdout = String::from_utf8_lossy(&output.stdout);
        let stderr = String::from_utf8_lossy(&output.stderr);
        let full_output = format!("{}{}", stdout, stderr);
        // Prepare the response
        let respond_with = format!("EXIT_CODE={}\nOUTPUT={}", exit_code, full_output);
        info!("Responding with: {}", respond_with);
        // Send the response back
        responder
            .send_multipart(vec![identity.to_vec(), respond_with.as_bytes().to_vec()], 0)
            .unwrap();
    }
}
