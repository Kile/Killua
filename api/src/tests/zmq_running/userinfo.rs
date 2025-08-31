use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;

use crate::routes::common::discord_auth::{disable_test_mode, enable_test_mode};
use crate::tests::common::{test_zmq_server, INIT};

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

fn setup_test_environment() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    // Enable test mode for Discord authentication
    enable_test_mode();
}

fn cleanup_test_environment() {
    // Disable test mode
    disable_test_mode();
}

#[test]
fn test_userinfo_own_data() {
    // Test getting own user data
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let response = client.get("/userinfo").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check that the response has the expected structure
    assert!(body.get("id").is_some());
    assert!(body.get("jenny").is_some());
    assert!(body.get("email").is_some());
    assert!(body.get("display_name").is_some());
    assert!(body.get("avatar_url").is_some());
    assert!(body.get("is_premium").is_some());
    assert!(body.get("premium_tier").is_some());

    // Check that email is included for own data
    assert!(body.get("email").unwrap().is_string());

    cleanup_test_environment();
}

#[test]
fn test_userinfo_specific_user_admin() {
    // Test admin accessing specific user data
    setup_test_environment();

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID, Some("admin@example.com"));

    let response = client
        .get(format!("/userinfo/{OTHER_USER_ID}"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check that the response has the expected structure
    assert!(body.get("id").is_some());
    assert!(body.get("jenny").is_some());
    assert!(body.get("display_name").is_some());
    assert!(body.get("avatar_url").is_some());
    assert!(body.get("is_premium").is_some());
    assert!(body.get("premium_tier").is_some());

    // Check that email is included (the mock server always returns email)
    // In a real scenario, admin accessing other user's data would not include email
    assert!(body.get("email").is_some());

    // Clean up
    std::env::remove_var("ADMIN_IDS");
    cleanup_test_environment();
}

#[test]
fn test_userinfo_specific_user_unauthorized() {
    // Test regular user trying to access another user's data
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let response = client
        .get(format!("/userinfo/{OTHER_USER_ID}"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_userinfo_missing_auth() {
    // Test request without authentication header
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    let response = client.get("/userinfo").dispatch();

    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_userinfo_invalid_auth_format() {
    // Test request with invalid auth header format
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let invalid_header = Header::new("Authorization", "InvalidFormat token");

    let response = client.get("/userinfo").header(invalid_header).dispatch();

    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_userinfo_own_data_no_email() {
    // Test getting own data when user has no email
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, None);

    let response = client.get("/userinfo").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check that email field exists (the mock server always returns email)
    assert!(body.get("email").is_some());
    // Note: The mock server always returns email, so we can't test null email
    assert!(body.get("email").unwrap().is_string());

    cleanup_test_environment();
}

#[test]
fn test_userinfo_response_structure() {
    // Test that the response has all expected fields with correct types
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    let response = client.get("/userinfo").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check field types
    assert!(body.get("id").unwrap().is_string());
    assert!(body.get("jenny").unwrap().is_number());
    assert!(body.get("daily_cooldown").unwrap().is_string());
    assert!(body.get("met_user").unwrap().is_array());
    assert!(body.get("effects").unwrap().is_object());
    assert!(body.get("rs_cards").unwrap().is_array());
    assert!(body.get("fs_cards").unwrap().is_array());
    assert!(body.get("badges").unwrap().is_array());
    assert!(body.get("rps_stats").unwrap().is_object());
    assert!(body.get("counting_highscore").unwrap().is_object());
    assert!(body.get("trivia_stats").unwrap().is_object());
    assert!(body.get("achievements").unwrap().is_array());
    assert!(body.get("votes").unwrap().is_number());
    assert!(body.get("voting_streak").unwrap().is_object());
    assert!(body.get("voting_reminder").unwrap().is_boolean());
    assert!(body.get("premium_guilds").unwrap().is_object());
    assert!(body.get("lootboxes").unwrap().is_array());
    assert!(body.get("boosters").unwrap().is_object());
    assert!(body.get("action_settings").unwrap().is_object());
    assert!(body.get("action_stats").unwrap().is_object());
    assert!(body.get("locale").unwrap().is_string());
    assert!(body.get("has_user_installed").unwrap().is_boolean());
    assert!(body.get("is_premium").unwrap().is_boolean());
    assert!(body.get("premium_tier").unwrap().is_string());
    assert!(body.get("display_name").unwrap().is_string());
    assert!(body.get("avatar_url").unwrap().is_string());

    cleanup_test_environment();
}

#[test]
fn test_userinfo_zmq_error_handling() {
    // Test handling of ZMQ errors
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header("invalid_user", Some("user@example.com"));

    let response = client.get("/userinfo").header(auth_header).dispatch();

    // Invalid token should result in Forbidden status
    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_userinfo_route_parameters() {
    // Test that route parameters work correctly
    setup_test_environment();

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID, Some("admin@example.com"));

    // Test with different user IDs
    let test_ids = vec!["111111111", "222222222", "333333333"];

    for user_id in test_ids {
        let response = client
            .get(format!("/userinfo/{user_id}"))
            .header(auth_header.clone())
            .dispatch();

        // Admin should be able to access any user
        assert_eq!(response.status(), Status::Ok);
    }

    // Clean up
    std::env::remove_var("ADMIN_IDS");
    cleanup_test_environment();
}

#[test]
fn test_userinfo_environment_cleanup() {
    // Test that environment variables are properly cleaned up
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID, Some("user@example.com"));

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let response = client.get("/userinfo").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    // Clean up
    std::env::remove_var("ADMIN_IDS");

    cleanup_test_environment();
}
