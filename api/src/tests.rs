use super::rocket;
use rocket::local::blocking::Client;
use rocket::http::{Status, Header};
use zmq::{Context, Error, Message, REP};
use serde::{Serialize, Deserialize};

// use crate::routes::commands::Category;
// use crate::routes::stats::Stats;
// use crate::routes::vote::Vote;

/// Spins up a zmq server in the background that only returns once
/// witth the provided response.
fn serve_zmq<'a, T: Serialize + Deserialize<'a> + std::marker::Send + 'static>(respond_with: T) {
    let context = Context::new();
    let responder = context.socket(REP).unwrap();

    assert!(responder.set_rcvtimeo(5000).is_ok());
    assert!(responder.set_linger(0).is_ok());
    responder.bind("ipc:///tmp/killua.ipc").unwrap();
    
    // Wait for a request in the background
    std::thread::spawn(move || {
        let mut msg = Message::new();
        let _ = responder.recv(&mut msg, 0).unwrap();
        let request_json = serde_json::to_string(&respond_with).unwrap();
        responder.send(request_json.as_bytes(), 0).unwrap();
        // Disconnect
        assert!(responder.unbind("ipc:///tmp/killua.ipc").is_ok());
    });
}
static KEY_CACHE: std::sync::Mutex<Option<String>> = std::sync::Mutex::new(None);

/// Gets the API key from Rocket.toml
fn get_key() -> String {
    if let Some(key) = KEY_CACHE.lock().unwrap().as_ref() {
        return key.to_owned();
    }
    let config = std::fs::read_to_string("Rocket.toml").unwrap();
    let config: toml::Value = toml::from_str(&config).unwrap();
    let key = config["global"]["api_key"].as_str().unwrap().to_owned();
    *KEY_CACHE.lock().unwrap() = Some(key.clone());
    key
}

#[test]
fn test_get_stats() {
    let stats = r#"{"guilds": 1, "shards": 1, "registered_users": 1, "last_restart": 1.0}"#;
    serve_zmq(stats);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), stats);
}

#[test]
fn test_get_stats_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to get stats"}"#);
}

#[test]
fn get_commands() {
    let commands = r#"{"CATEGORY": {"name": "category", "description": "", "emoji": {"normal": "a", "unicode": "b"}, "commands": []}}"#;
    serve_zmq(commands);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), commands);
}

fn get_commands_twice() {
    let commands = r#"{"CATEGORY": {"name": "category", "description": "", "emoji": {"normal": "a", "unicode": "b"}, "commands": []}}"#;
    serve_zmq(commands);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), commands);

    // Should have cached commands so not need a zmq server to be active
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), commands);
}

#[test]
fn get_commands_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to get commands"}"#);
}

#[test]
fn error_then_success() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to get commands"}"#);

    get_commands_twice();
}

#[test]
fn vote() {
    let vote = r#"{"user": 1, "id": "1", "isWeekend": true}"#;
    serve_zmq(vote);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(vote)
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), r#"{"message":"Success"}"#);
}

#[test]
fn vote_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to register vote"}"#);
}

#[test]
fn vote_invalid_key() {
    let vote = r#"{"user": 1, "id": "1", "isWeekend": true}"#;
    serve_zmq(vote);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(vote)
        .header(Header::new("Authorization", "invalid"))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn vote_missing_key() {
    let vote = r#"{"user": 1, "id": "1", "isWeekend": true}"#;
    serve_zmq(vote);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(vote)
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn vote_invalid_json() {
    let vote = r#"{"user": 1, "id": "1", "isWeekend": true"#;
    serve_zmq(vote);

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(vote)
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to register vote"}"#);
}