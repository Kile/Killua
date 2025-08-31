use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::routes::common::discord_auth::{disable_test_mode, enable_test_mode};

// Test fixtures
const TEST_USER_ID: &str = "123456789";

fn create_auth_header(user_id: &str) -> Header<'static> {
    // Map user IDs to the correct test tokens
    let token = match user_id {
        "123456789" => "Bearer valid_token_1",
        _ => "Bearer invalid_token",
    };

    Header::new("Authorization", token)
}

#[test]
fn test_userinfo_zmq_down() {
    // Test userinfo when ZMQ server is down
    // Enable test mode for Discord authentication
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client.get("/userinfo").header(auth_header).dispatch();

    // Should return an error when ZMQ server is down
    // The exact error depends on how the application handles ZMQ failures
    // It could be InternalServerError, BadRequest, or ServiceUnavailable
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    // Disable test mode
    disable_test_mode();
}

#[test]
fn test_userinfo_by_id_zmq_down() {
    // Test userinfo by ID when ZMQ server is down
    // Enable test mode for Discord authentication
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get("/userinfo/123456789")
        .header(auth_header)
        .dispatch();

    // Should return an error when ZMQ server is down
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    // Disable test mode
    disable_test_mode();
}

#[test]
fn test_userinfo_zmq_down_without_auth() {
    // Test userinfo when ZMQ server is down and no auth provided
    let client = Client::tracked(rocket()).unwrap();

    let response = client.get("/userinfo").dispatch();

    // Should return Forbidden due to missing auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_userinfo_zmq_down_invalid_auth() {
    // Test userinfo when ZMQ server is down with invalid auth
    // Enable test mode for Discord authentication
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let invalid_header = Header::new("Authorization", "Bearer invalid_token");

    let response = client.get("/userinfo").header(invalid_header).dispatch();

    // Should return Forbidden due to invalid auth, not ZMQ error
    assert_eq!(response.status(), Status::Forbidden);

    // Disable test mode
    disable_test_mode();
}
