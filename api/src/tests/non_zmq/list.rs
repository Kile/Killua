use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;
use std::fs;
use std::path::Path;

use crate::rocket;
use crate::routes::common::discord_auth::{
    disable_test_mode, enable_test_mode, set_test_admin_ids,
};

const ADMIN_USER_ID: &str = "555666777";

fn create_auth_header() -> Header<'static> {
    Header::new("Authorization", "Bearer admin_token")
}

fn setup_test_environment() {
    // Enable test mode for Discord authentication
    enable_test_mode();

    // Set test admin IDs
    set_test_admin_ids(ADMIN_USER_ID.to_string());

    // Set HASH_SECRET for image endpoint testing
    std::env::set_var("HASH_SECRET", "test_secret_key");
}

fn cleanup_test_environment() {
    disable_test_mode();
    std::env::remove_var("ADMIN_IDS");
    std::env::remove_var("HASH_SECRET");

    // Clean up the entire cdn directory
    let cdn_dir = Path::new("../assets/cdn");
    if cdn_dir.exists() {
        fs::remove_dir_all(cdn_dir).ok();
    }
}

#[test]
fn test_list_empty_directory() {
    setup_test_environment();
    cleanup_test_environment(); // Ensure clean state

    // Explicitly enable test mode again to ensure it's set
    enable_test_mode();
    set_test_admin_ids(ADMIN_USER_ID.to_string());

    let client = Client::tracked(rocket()).expect("valid rocket instance");
    let auth_header = create_auth_header();

    let response = client.get("/image/list").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(body.get("files").unwrap().as_array().unwrap().len(), 0);

    cleanup_test_environment();
}

#[test]
fn test_list_with_files() {
    setup_test_environment();
    cleanup_test_environment();

    // Explicitly enable test mode and set admin IDs
    enable_test_mode();
    set_test_admin_ids(ADMIN_USER_ID.to_string());

    let client = Client::tracked(rocket()).expect("valid rocket instance");
    let auth_header = create_auth_header();

    // Create some test files
    let cdn_dir = std::path::Path::new("../assets/cdn");
    std::fs::create_dir_all(cdn_dir).unwrap();
    std::fs::write(cdn_dir.join("test1.png"), b"test1").unwrap();
    std::fs::write(cdn_dir.join("test2.png"), b"test2").unwrap();
    std::fs::create_dir_all(cdn_dir.join("subdir")).unwrap();
    std::fs::write(cdn_dir.join("subdir").join("test3.png"), b"test3").unwrap();

    let response = client.get("/image/list").header(auth_header).dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    let files = body.get("files").unwrap().as_array().unwrap();
    assert_eq!(files.len(), 3);

    // Check that all expected files are present (order may vary due to sorting)
    let file_strings: Vec<String> = files
        .iter()
        .map(|f| f.as_str().unwrap().to_string())
        .collect();

    assert!(file_strings.contains(&"test1.png".to_string()));
    assert!(file_strings.contains(&"test2.png".to_string()));
    assert!(file_strings.contains(&"subdir/test3.png".to_string()));

    cleanup_test_environment();
}

#[test]
fn test_list_unauthorized() {
    setup_test_environment();

    let client = Client::tracked(rocket()).expect("valid rocket instance");

    let response = client.get("/image/list").dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    // The response body might be empty for 403, so we don't try to parse JSON
    // Just verify the status code is correct

    cleanup_test_environment();
}
