use crate::rocket;
use hex;
use rocket::http::{ContentType, Header, Status};
use rocket::local::blocking::Client;
use rocket::serde::json::json;
use sha2::{Digest, Sha256};

use crate::routes::common::discord_security::enable_test_mode;

// Test Discord public key (this is a test key, not a real one)
#[allow(dead_code)]
const TEST_PUBLIC_KEY: &str = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef";

// For testing purposes, we'll use a simple approach
// In production, this would be a real Ed25519 signature
fn create_test_signature(timestamp: &str, body: &str) -> String {
    // Create a simple hash-based signature for testing
    // This is not a real Ed25519 signature, but it's sufficient for testing the validation logic
    let mut hasher = Sha256::new();
    hasher.update(format!("{}{}", timestamp, body).as_bytes());
    let result = hasher.finalize();
    hex::encode(result)
}

#[test]
fn test_application_authorized_webhook_zmq_down() {
    // ZMQ server is down
    enable_test_mode();
    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 0,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {
                    "id": "123456789012345678",
                    "username": "testuser",
                    "discriminator": "1234",
                    "avatar": "test_avatar_hash",
                    "bot": false,
                    "system": false,
                    "mfa_enabled": true,
                    "verified": true,
                    "email": "test@example.com"
                }
            }
        }
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";
    let signature = create_test_signature(timestamp, &body);

    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Ed25519", signature))
        .header(Header::new("X-Signature-Timestamp", timestamp))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::InternalServerError);
}

#[test]
fn test_application_deauthorized_webhook_zmq_down() {
    // ZMQ server is down
    enable_test_mode();
    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 0,
        "event": {
            "type": "APPLICATION_DEAUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "user": {
                    "id": "123456789012345678",
                    "username": "testuser",
                    "discriminator": "1234",
                    "avatar": "test_avatar_hash",
                    "bot": false,
                    "system": false,
                    "mfa_enabled": true,
                    "verified": true,
                    "email": "test@example.com"
                }
            }
        }
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";
    let signature = create_test_signature(timestamp, &body);

    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Ed25519", signature))
        .header(Header::new("X-Signature-Timestamp", timestamp))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::InternalServerError);
}

#[test]
fn test_webhook_ping_event_no_auth_zmq_down() {
    // ZMQ server is down, but ping should still work without auth
    enable_test_mode();
    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 0
    });

    let body = serde_json::to_string(&webhook_data).unwrap();

    // No authentication headers for ping events
    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::NoContent);
}

#[test]
fn test_webhook_ping_event_zmq_down() {
    // ZMQ server is down, but ping should still work
    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 0
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";
    let signature = create_test_signature(timestamp, &body);

    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Ed25519", signature))
        .header(Header::new("X-Signature-Timestamp", timestamp))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::NoContent);
}

#[test]
fn test_webhook_health_check_zmq_down() {
    // ZMQ server is down, but health check should still work
    enable_test_mode();
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/webhooks/discord").dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body = response.into_string().expect("response body");
    let response_data: serde_json::Value = serde_json::from_str(&body).expect("valid json");

    assert_eq!(response_data["success"], true);
    assert_eq!(
        response_data["message"],
        "Discord webhook endpoint is active"
    );
}
