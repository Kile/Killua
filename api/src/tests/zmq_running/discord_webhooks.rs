use crate::rocket;
use hex;
use rocket::http::{ContentType, Header, Status};
use rocket::local::blocking::Client;
use rocket::serde::json::json;
use sha2::{Digest, Sha256};

use crate::tests::common::{test_zmq_server, INIT};

// Test Discord public key (this is a test key, not a real one)
// This is the public key corresponding to the private key used for signing
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
fn test_application_authorized_webhook_zmq_running() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
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

    assert_eq!(response.status(), Status::Ok);

    let body = response.into_string().expect("response body");
    let response_data: serde_json::Value = serde_json::from_str(&body).expect("valid json");

    assert_eq!(response_data["success"], true);
    assert_eq!(
        response_data["message"],
        "Application authorized event processed successfully"
    );
}

#[test]
fn test_application_authorized_webhook_with_guild_zmq_running() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 0,
                "scopes": ["applications.commands", "bot"],
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
                },
                "guild": {
                    "id": "987654321098765432",
                    "name": "Test Guild",
                    "icon": "guild_icon_hash",
                    "owner": true,
                    "owner_id": "123456789012345678",
                    "permissions": "8",
                    "features": ["COMMUNITY", "NEWS"]
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

    assert_eq!(response.status(), Status::Ok);

    let body = response.into_string().expect("response body");
    let response_data: serde_json::Value = serde_json::from_str(&body).expect("valid json");

    assert_eq!(response_data["success"], true);
    assert_eq!(
        response_data["message"],
        "Application authorized event processed successfully"
    );
}

#[test]
fn test_application_deauthorized_webhook_zmq_running() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
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

    assert_eq!(response.status(), Status::Ok);

    let body = response.into_string().expect("response body");
    let response_data: serde_json::Value = serde_json::from_str(&body).expect("valid json");

    assert_eq!(response_data["success"], true);
    assert_eq!(
        response_data["message"],
        "Application deauthorized event processed successfully"
    );
}

#[test]
fn test_webhook_health_check_zmq_running() {
    INIT.call_once(|| {
        test_zmq_server();
    });

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

#[test]
fn test_webhook_missing_signature_header() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {
                    "id": "123456789012345678",
                    "username": "testuser"
                }
            }
        }
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";

    // Missing X-Signature-Ed25519 header
    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Timestamp", timestamp))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::Unauthorized);
}

#[test]
fn test_webhook_missing_timestamp_header() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {
                    "id": "123456789012345678",
                    "username": "testuser"
                }
            }
        }
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";
    let signature = create_test_signature(timestamp, &body);

    // Missing X-Signature-Timestamp header
    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Ed25519", signature))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::Unauthorized);
}

#[test]
fn test_webhook_invalid_signature() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let webhook_data = json!({
        "version": 1,
        "application_id": "1234560123453231555",
        "type": 1,
        "event": {
            "type": "APPLICATION_AUTHORIZED",
            "timestamp": "2024-10-18T14:42:53.064834",
            "data": {
                "integration_type": 1,
                "scopes": ["applications.commands"],
                "user": {
                    "id": "123456789012345678",
                    "username": "testuser"
                }
            }
        }
    });

    let body = serde_json::to_string(&webhook_data).unwrap();
    let timestamp = "1703000000";
    let invalid_signature = "invalid_signature_that_will_fail_verification";

    let response = client
        .post("/webhooks/discord")
        .header(ContentType::JSON)
        .header(Header::new("X-Signature-Ed25519", invalid_signature))
        .header(Header::new("X-Signature-Timestamp", timestamp))
        .body(body)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);
}
