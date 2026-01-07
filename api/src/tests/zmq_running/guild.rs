use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;

use crate::routes::common::discord_auth::{
    clear_test_guild_permissions, disable_test_mode, enable_test_mode, set_test_guild_permissions,
};
use crate::tests::common::{test_zmq_server, INIT};

// Test fixtures
const TEST_USER_ID: &str = "123456789";
const ADMIN_USER_ID: &str = "555666777";
const OTHER_USER_ID: &str = "987654321";
const TEST_GUILD_ID: &str = "111222333444555666";
const OTHER_GUILD_ID: &str = "777888999000111222";

fn create_auth_header(user_id: &str) -> Header<'static> {
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
    // Clear test guild permissions
    clear_test_guild_permissions();
    // Disable test mode
    disable_test_mode();
}

#[test]
fn test_guild_info_with_permission() {
    // Test getting guild info with proper MANAGE_SERVER permission
    setup_test_environment();

    // Set guild permissions: user has MANAGE_SERVER (32) for the test guild
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check that the response has the expected structure
    assert!(body.get("member_count").is_some());
    assert!(body.get("prefix").is_some());
    assert!(body.get("is_premium").is_some());
    assert!(body.get("tags").is_some());

    cleanup_test_environment();
}

#[test]
fn test_guild_info_admin_access() {
    // Test admin accessing any guild info
    setup_test_environment();

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("member_count").is_some());

    // Clean up
    std::env::remove_var("ADMIN_IDS");
    cleanup_test_environment();
}

#[test]
fn test_guild_info_without_permission() {
    // Test accessing guild info without MANAGE_SERVER permission
    setup_test_environment();

    // Set guild permissions: user does NOT have MANAGE_SERVER for this guild
    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    // Should fail due to lack of permission
    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("MANAGE_SERVER"));

    cleanup_test_environment();
}

#[test]
fn test_guild_info_missing_auth() {
    // Test request without authentication header
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_guild_info_response_structure() {
    // Test that the response has all expected fields with correct types
    setup_test_environment();

    // Set guild permissions
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check field types
    assert!(body.get("member_count").unwrap().is_number());
    assert!(body.get("prefix").unwrap().is_string());
    assert!(body.get("is_premium").unwrap().is_boolean());
    assert!(body.get("tags").unwrap().is_array());

    // Check tags structure
    let tags = body.get("tags").unwrap().as_array().unwrap();
    if !tags.is_empty() {
        let tag = &tags[0];
        assert!(tag.get("name").unwrap().is_string());
        assert!(tag.get("created_at").unwrap().is_string());
        assert!(tag.get("content").unwrap().is_string());
        assert!(tag.get("uses").unwrap().is_number());

        // Check owner structure (now an object with user_id, display_name, avatar_url)
        let owner = tag.get("owner").unwrap();
        assert!(owner.is_object());
        assert!(owner.get("user_id").unwrap().is_number());
        assert!(owner.get("display_name").unwrap().is_string());
        // avatar_url can be null or string
        let avatar = owner.get("avatar_url").unwrap();
        assert!(avatar.is_null() || avatar.is_string());
    }

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_prefix_with_permission() {
    // Test editing guild prefix with MANAGE_SERVER permission
    setup_test_environment();

    // Set guild permissions: user has MANAGE_SERVER (32) for the test guild
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let edit_data = serde_json::json!({
        "prefix": "?"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert!(body.get("message").is_some());

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_admin_access() {
    // Test admin editing any guild
    setup_test_environment();

    // Set admin IDs for this test
    std::env::set_var("ADMIN_IDS", ADMIN_USER_ID);

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let edit_data = serde_json::json!({
        "prefix": "$"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    // Clean up
    std::env::remove_var("ADMIN_IDS");
    cleanup_test_environment();
}

#[test]
fn test_guild_edit_without_permission() {
    // Test editing guild without MANAGE_SERVER permission
    setup_test_environment();

    // Set guild permissions: user does NOT have MANAGE_SERVER for this guild
    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let edit_data = serde_json::json!({
        "prefix": "?"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("MANAGE_SERVER"));

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_empty_request() {
    // Test request with no fields to edit
    setup_test_environment();

    // Set guild permissions
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body("{}")
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("No valid fields"));

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_missing_auth() {
    // Test request without authentication header
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    let edit_data = serde_json::json!({
        "prefix": "?"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_invalid_json() {
    // Test request with invalid JSON
    setup_test_environment();

    // Set guild permissions
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body("{ invalid json }")
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_guild_edit_response_structure() {
    // Test that the response has the expected structure
    setup_test_environment();

    // Set guild permissions
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let edit_data = serde_json::json!({
        "prefix": "!"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check response structure
    assert!(body.get("success").unwrap().is_boolean());
    assert!(body.get("message").unwrap().is_string());

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_authenticated() {
    // Test getting editable guilds while authenticated
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "guild_ids": [111222333444555666_i64, 777888999000111222_i64, 999888777666555444_i64]
    });

    let response = client
        .post("/guild/editable")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("editable").is_some());
    assert!(body.get("editable").unwrap().is_array());

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_response_structure() {
    // Test that the response has the expected structure
    setup_test_environment();

    // Set up test permissions for the user to have MANAGE_SERVER on the test guild
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "guild_ids": [111222333444555666_i64]
    });

    let response = client
        .post("/guild/editable")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check response structure
    assert!(body.get("editable").unwrap().is_array());
    assert!(body.get("premium").unwrap().is_array());

    // User has MANAGE_SERVER on the test guild, so it should be returned
    let editable = body.get("editable").unwrap().as_array().unwrap();
    assert!(!editable.is_empty());

    // Premium field should also be present (already verified as array above)
    assert_eq!(editable[0].as_i64().unwrap(), 111222333444555666_i64);

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_missing_auth() {
    // Test request without authentication header
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "guild_ids": [111222333444555666_i64]
    });

    let response = client
        .post("/guild/editable")
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_empty_list() {
    // Test with empty guild_ids list
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "guild_ids": []
    });

    let response = client
        .post("/guild/editable")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_invalid_json() {
    // Test request with invalid JSON
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .post("/guild/editable")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body("{ invalid json }")
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_guild_editable_different_users() {
    // Test that different users get their own editable guilds
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    // First user
    let auth_header_1 = create_auth_header(TEST_USER_ID);
    let payload = serde_json::json!({
        "guild_ids": [111222333444555666_i64]
    });

    let response_1 = client
        .post("/guild/editable")
        .header(auth_header_1)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response_1.status(), Status::Ok);

    // Second user
    let auth_header_2 = create_auth_header(OTHER_USER_ID);
    let response_2 = client
        .post("/guild/editable")
        .header(auth_header_2)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response_2.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_guild_multiple_permissions() {
    // Test user with multiple guild permissions
    setup_test_environment();

    // Set permissions for multiple guilds
    set_test_guild_permissions(format!(
        "{}:{}:32,{}:{}:32",
        TEST_USER_ID, TEST_GUILD_ID, TEST_USER_ID, OTHER_GUILD_ID
    ));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    // Should be able to access first guild
    let response_1 = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header.clone())
        .dispatch();

    assert_eq!(response_1.status(), Status::Ok);

    // Should be able to access second guild
    let response_2 = client
        .get(format!("/guild/{OTHER_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response_2.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_guild_permission_exact_match() {
    // Test that MANAGE_SERVER permission flag is correctly checked
    setup_test_environment();

    // Set permission to exactly MANAGE_SERVER (32)
    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_guild_permission_combined_flags() {
    // Test that MANAGE_SERVER works when combined with other permission flags
    setup_test_environment();

    // Set permission to MANAGE_SERVER (32) + other flags (e.g., 1 + 2 + 32 = 35)
    set_test_guild_permissions(format!("{}:{}:35", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_guild_permission_without_manage_server() {
    // Test that other permissions without MANAGE_SERVER are rejected
    setup_test_environment();

    // Set permission to other flags but NOT MANAGE_SERVER (e.g., 1 + 2 + 4 = 7, no 32)
    set_test_guild_permissions(format!("{}:{}:7", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let response = client
        .get(format!("/guild/{TEST_GUILD_ID}/info"))
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_tag_create_with_permission() {
    // Test creating a tag with MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "welcome",
        "content": "Welcome to the server!"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/create"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert!(body.get("message").is_some());

    cleanup_test_environment();
}

#[test]
fn test_tag_create_without_permission() {
    // Test creating a tag without MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test",
        "content": "Test content"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/create"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_tag_create_empty_name() {
    // Test creating a tag with empty name
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "",
        "content": "Some content"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/create"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("empty"));

    cleanup_test_environment();
}

#[test]
fn test_tag_create_missing_auth() {
    // Test creating a tag without authentication
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "name": "test",
        "content": "Test content"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/create"))
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_tag_edit_with_permission() {
    // Test editing a tag with MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "welcome",
        "content": "Updated welcome message!"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    cleanup_test_environment();
}

#[test]
fn test_tag_edit_rename() {
    // Test renaming a tag
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "old_name",
        "new_name": "new_name"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_tag_edit_without_permission() {
    // Test editing a tag without MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test",
        "content": "Updated content"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_tag_edit_no_fields() {
    // Test editing a tag without providing any fields to update
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test"
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("No valid fields"));

    cleanup_test_environment();
}

#[test]
fn test_tag_delete_with_permission() {
    // Test deleting a tag with MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "old_tag"
    });

    let response = client
        .delete(format!("/guild/{TEST_GUILD_ID}/tag/delete"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    cleanup_test_environment();
}

#[test]
fn test_tag_delete_without_permission() {
    // Test deleting a tag without MANAGE_SERVER permission
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "test"
    });

    let response = client
        .delete(format!("/guild/{TEST_GUILD_ID}/tag/delete"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_tag_delete_empty_name() {
    // Test deleting a tag with empty name
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": ""
    });

    let response = client
        .delete(format!("/guild/{TEST_GUILD_ID}/tag/delete"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body
        .get("error")
        .unwrap()
        .as_str()
        .unwrap()
        .contains("empty"));

    cleanup_test_environment();
}

#[test]
fn test_tag_delete_missing_auth() {
    // Test deleting a tag without authentication
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();

    let payload = serde_json::json!({
        "name": "test"
    });

    let response = client
        .delete(format!("/guild/{TEST_GUILD_ID}/tag/delete"))
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_tag_transfer_with_permission() {
    // Test transferring a tag with MANAGE_SERVER permission
    // Note: Actual ownership verification happens on the bot side
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "welcome",
        "new_owner": 987654321_i64
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Request should succeed (bot handles ownership verification)
    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").is_some());

    cleanup_test_environment();
}

#[test]
fn test_tag_transfer_without_permission() {
    // Test that tag transfer requires MANAGE_SERVER permission
    setup_test_environment();

    // No permissions
    set_test_guild_permissions(format!("{}:{}:0", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "welcome",
        "new_owner": 987654321_i64
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    // Should be denied without MANAGE_SERVER permission
    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_tag_edit_with_transfer_and_content() {
    // Test editing content and transferring ownership at the same time
    setup_test_environment();

    set_test_guild_permissions(format!("{}:{}:32", TEST_USER_ID, TEST_GUILD_ID));

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let payload = serde_json::json!({
        "name": "welcome",
        "content": "New content",
        "new_owner": 987654321_i64
    });

    let response = client
        .post(format!("/guild/{TEST_GUILD_ID}/tag/edit"))
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(payload.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}
