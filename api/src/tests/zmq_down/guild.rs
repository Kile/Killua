use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::routes::common::discord_auth::{
    disable_test_mode, enable_test_mode, set_test_guild_permissions,
};

// Test fixtures
const TEST_USER_ID: &str = "123456789";
const TEST_GUILD_ID: i64 = 111222333444555666;

fn create_auth_header(user_id: &str) -> Header<'static> {
    // Map user IDs to the correct test tokens
    let token = match user_id {
        "123456789" => "Bearer valid_token_1",
        _ => "Bearer invalid_token",
    };

    Header::new("Authorization", token)
}

#[test]
fn test_guild_info_zmq_down() {
    // Test guild info when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{}/info", TEST_GUILD_ID))
        .header(auth_header)
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_guild_info_zmq_down_without_auth() {
    // Test guild info when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let response = client
        .get(format!("/guild/{}/info", TEST_GUILD_ID))
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_guild_info_zmq_down_invalid_auth() {
    // Test guild info when ZMQ server is down with invalid auth
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let invalid_header = Header::new("Authorization", "Bearer invalid_token");

    let response = client
        .get(format!("/guild/{}/info", TEST_GUILD_ID))
        .header(invalid_header)
        .dispatch();

    // Should return Forbidden due to invalid auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);

    disable_test_mode();
}

#[test]
fn test_guild_edit_zmq_down() {
    // Test guild edit when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let edit_data = serde_json::json!({
        "prefix": "!"
    });

    let response = client
        .post(format!("/guild/{}/edit", TEST_GUILD_ID))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_guild_edit_zmq_down_without_auth() {
    // Test guild edit when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let edit_data = serde_json::json!({
        "prefix": "!"
    });

    let response = client
        .post(format!("/guild/{}/edit", TEST_GUILD_ID))
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_guild_editable_zmq_down() {
    // Test guild editable when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "guild_ids": [TEST_GUILD_ID]
    });

    let response = client
        .post("/guild/editable")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_guild_editable_zmq_down_without_auth() {
    // Test guild editable when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "guild_ids": [TEST_GUILD_ID]
    });

    let response = client
        .post("/guild/editable")
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_tag_create_zmq_down() {
    // Test tag create when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test_tag",
        "content": "Test content"
    });

    let response = client
        .post(format!("/guild/{}/tag/create", TEST_GUILD_ID))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_tag_create_zmq_down_without_auth() {
    // Test tag create when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "name": "test_tag",
        "content": "Test content"
    });

    let response = client
        .post(format!("/guild/{}/tag/create", TEST_GUILD_ID))
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_tag_edit_zmq_down() {
    // Test tag edit when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test_tag",
        "content": "Updated content"
    });

    let response = client
        .post(format!("/guild/{}/tag/edit", TEST_GUILD_ID))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_tag_edit_zmq_down_without_auth() {
    // Test tag edit when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "name": "test_tag",
        "content": "Updated content"
    });

    let response = client
        .post(format!("/guild/{}/tag/edit", TEST_GUILD_ID))
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_tag_delete_zmq_down() {
    // Test tag delete when ZMQ server is down
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test_tag"
    });

    let response = client
        .delete(format!("/guild/{}/tag/delete", TEST_GUILD_ID))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_tag_delete_zmq_down_without_auth() {
    // Test tag delete when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "name": "test_tag"
    });

    let response = client
        .delete(format!("/guild/{}/tag/delete", TEST_GUILD_ID))
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_command_usage_zmq_down() {
    enable_test_mode();
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));
    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);
    let now = chrono::Utc::now().timestamp() as f64;
    let from = now - 86400.0;
    let to = now;
    let response = client
        .get(format!(
            "/guild/{}/command-usage?from={}&to={}&interval=1h",
            TEST_GUILD_ID, from, to
        ))
        .header(auth_header)
        .dispatch();
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );
    disable_test_mode();
}

#[test]
fn test_command_usage_zmq_down_without_auth() {
    let client = Client::tracked(rocket()).unwrap();
    let now = chrono::Utc::now().timestamp() as f64;
    let from = now - 86400.0;
    let to = now;
    let response = client
        .get(format!(
            "/guild/{}/command-usage?from={}&to={}&interval=1h",
            TEST_GUILD_ID, from, to
        ))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}
