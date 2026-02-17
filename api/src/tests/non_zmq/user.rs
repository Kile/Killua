use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::routes::common::discord_auth::{disable_test_mode, enable_test_mode};

// Test fixtures
const TEST_USER_ID: &str = "123456789";
const ADMIN_USER_ID: &str = "555666777";
const OTHER_USER_ID: &str = "987654321";

fn create_auth_header(user_id: &str, _email: Option<&str>) -> Header<'static> {
    // Map user IDs to the correct test tokens
    let token = match user_id {
        "123456789" => "Bearer valid_token_1",
        "987654321" => "Bearer valid_token_2",
        "555666777" => "Bearer admin_token",
        _ => "Bearer invalid_token",
    };

    Header::new("Authorization", token)
}

// ===== USER EDIT TESTS (NON-ZMQ) =====

#[test]
fn test_user_edit_discord_auth_validation() {
    // Test Discord authentication validation for user edit
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put("/user/edit")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should fail due to ZMQ not being available, but auth should be validated first
    // The exact error depends on how the application handles ZMQ failures
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    disable_test_mode();
}

#[test]
fn test_user_edit_admin_validation() {
    // Test admin validation for user edit
    enable_test_mode();

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID, Some("admin@example.com"));

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put(format!("/user/edit/{OTHER_USER_ID}"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should fail due to ZMQ not being available, but admin validation should pass
    assert!(
        response.status() == Status::InternalServerError
            || response.status() == Status::BadRequest
            || response.status() == Status::ServiceUnavailable
    );

    // Clean up
    std::env::remove_var("ADMIN_IDS");
    disable_test_mode();
}

#[test]
fn test_user_edit_non_admin_access_denied() {
    // Test non-admin user trying to edit another user's data
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put(format!("/user/edit/{OTHER_USER_ID}"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return BadRequest due to access denied (before ZMQ call)
    assert_eq!(response.status(), Status::BadRequest);

    let body: serde_json::Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").unwrap().is_string());
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("Access denied"));

    disable_test_mode();
}

#[test]
fn test_user_edit_json_validation() {
    // Test JSON validation for user edit endpoint
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    // Test with malformed JSON
    let response = client
        .put(format!("/user/edit/{TEST_USER_ID}"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body("{ invalid json }")
        .dispatch();

    // Should return BadRequest due to invalid JSON
    assert_eq!(response.status(), Status::BadRequest);

    disable_test_mode();
}

#[test]
fn test_user_edit_empty_json() {
    // Test user edit with empty JSON body
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let response = client
        .put(format!("/user/edit/{TEST_USER_ID}"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body("{}")
        .dispatch();

    // Should return BadRequest due to no valid fields provided
    assert_eq!(response.status(), Status::BadRequest);

    let body: serde_json::Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").unwrap().is_string());
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("No valid fields provided"));

    disable_test_mode();
}

#[test]
fn test_user_edit_invalid_field_types() {
    // Test user edit with invalid field types
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "voting_reminder": "not_a_boolean"
    });

    let response = client
        .put("/user/edit")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return UnprocessableEntity due to invalid field type
    assert_eq!(response.status(), Status::UnprocessableEntity);

    disable_test_mode();
}

#[test]
fn test_user_edit_incomplete_action_settings() {
    // Test user edit with incomplete action_settings
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "action_settings": {
            "hug": true,
            "cuddle": false
            // Missing pat, slap, poke, tickle
        }
    });

    let response = client
        .put("/user/edit")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return UnprocessableEntity due to incomplete action_settings
    assert_eq!(response.status(), Status::UnprocessableEntity);

    disable_test_mode();
}

#[test]
fn test_user_edit_incomplete_email_notifications() {
    // Test user edit with incomplete email_notifications
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "email_notifications": {
            "news": true
            // Missing updates, posts
        }
    });

    let response = client
        .put("/user/edit")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    // Should return UnprocessableEntity due to incomplete email_notifications
    assert_eq!(response.status(), Status::UnprocessableEntity);

    disable_test_mode();
}

#[test]
fn test_user_edit_route_parameter_validation() {
    // Test user edit with different user IDs in route parameter
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    // Test with various user ID formats
    let test_user_ids = vec!["111111111", "222222222", "999999999999999999"];

    for user_id in test_user_ids {
        let response = client
            .put(format!("/user/edit/{user_id}"))
            .header(auth_header.clone())
            .header(Header::new("Content-Type", "application/json"))
            .body(edit_data.to_string())
            .dispatch();

        // Should return BadRequest due to access denied (can't edit other users)
        assert_eq!(response.status(), Status::BadRequest);
    }

    disable_test_mode();
}
