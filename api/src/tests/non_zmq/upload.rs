use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

use crate::routes::common::discord_auth::{
    disable_test_mode, enable_test_mode, set_test_admin_ids,
};
use crate::routes::image::{sha256, HASH_SECRET};

// Test fixtures
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

fn verify_file_upload(client: &Client, expected_path: &str, expected_data: &[u8]) {
    // Verify file was saved correctly locally
    let file_path_str = format!("../assets/cdn/{}", expected_path.replace("cdn/", ""));
    let file_path = Path::new(&file_path_str);
    assert!(file_path.exists());
    let saved_data = fs::read(file_path).unwrap();
    assert_eq!(saved_data, expected_data);

    // Verify file is accessible via the image endpoint
    let expiry = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs()
        + 3600;
    let expiry_str = expiry.to_string();

    // Normalize the path for the image endpoint (remove double slashes)
    let normalized_path = expected_path.replace("//", "/");
    let token = sha256(&normalized_path, &expiry_str, &HASH_SECRET);

    let response = client
        .get(format!(
            "/image/{normalized_path}?token={token}&expiry={expiry}",
        ))
        .dispatch();

    assert_eq!(response.status(), Status::Ok);
    let response_data = response.into_bytes().unwrap();
    assert_eq!(response_data, expected_data);

    // Verify file appears in the list endpoint
    let auth_header = create_auth_header();
    let list_response = client.get("/image/list").header(auth_header).dispatch();
    assert_eq!(list_response.status(), Status::Ok);

    let list_body: Value = serde_json::from_str(&list_response.into_string().unwrap()).unwrap();
    let files = list_body.get("files").unwrap().as_array().unwrap();

    // Extract just the filename from the expected path
    let expected_filename = expected_path.replace("cdn/", "");
    let file_strings: Vec<String> = files
        .iter()
        .map(|f| f.as_str().unwrap().to_string())
        .collect();

    assert!(
        file_strings.contains(&expected_filename),
        "File {expected_filename} not found in list: {file_strings:?}",
    );
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
fn test_upload_valid_file() {
    // Test uploading a valid file with directory and filename
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // Create test image data (PNG header + some data)
    let test_image_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xdc\xcc\xe1\x00\x00\x00\x00IEND\xaeB`\x82";

    let response = client
        .post("/image/upload?path=test/test.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("path").unwrap().as_str().unwrap(),
        "cdn/test/test.png"
    );

    verify_file_upload(&client, "cdn/test/test.png", test_image_data);

    cleanup_test_environment();
}

#[test]
fn test_upload_filename_only() {
    // Test uploading a file with only filename (no directory)
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=test2.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    // This should succeed since directory is optional
    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(body.get("path").unwrap().as_str().unwrap(), "cdn/test2.png");

    // Verify file upload using helper function
    verify_file_upload(&client, "cdn/test2.png", test_image_data);

    cleanup_test_environment();
}

#[test]
fn test_upload_directory_only() {
    // Test uploading a file with only directory (no filename)
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=test")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(body.get("path").unwrap().as_str().unwrap(), "cdn/test");

    cleanup_test_environment();
}

#[test]
fn test_upload_invalid_filename() {
    // Test uploading with invalid filename containing path separators
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=test/../test.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(body.get("error").unwrap().as_str().unwrap(), "Invalid path");

    cleanup_test_environment();
}

#[test]
fn test_upload_invalid_directory() {
    // Test uploading with invalid directory containing traversal
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=../../test.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(body.get("error").unwrap().as_str().unwrap(), "Invalid path");

    cleanup_test_environment();
}

#[test]
fn test_upload_empty_filename() {
    // Test uploading with empty filename
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=test/")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(body.get("path").unwrap().as_str().unwrap(), "cdn/test");

    cleanup_test_environment();
}

#[test]
fn test_upload_empty_directory() {
    // Test uploading with empty directory parameter
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"test image data";

    let response = client
        .post("/image/upload?path=/test.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(body.get("path").unwrap().as_str().unwrap(), "cdn/test.png");

    // Verify file upload using helper function
    verify_file_upload(&client, "cdn/test.png", test_image_data);

    cleanup_test_environment();
}

#[test]
fn test_upload_file_size_limit() {
    // Test uploading a file that should be within the size limit
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // Create a file that should be within the 10 MiB limit
    let data = vec![0u8; 5 * 1024 * 1024]; // 5 MiB

    let response = client
        .post("/image/upload?path=test/size_test.png")
        .header(auth_header)
        .body(data)
        .dispatch();

    // This should succeed
    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    cleanup_test_environment();
}

#[test]
fn test_upload_nested_directory() {
    // Test uploading to a nested directory structure
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"nested test image data";

    let response = client
        .post("/image/upload?path=test/nested/nested.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("path").unwrap().as_str().unwrap(),
        "cdn/test/nested/nested.png"
    );

    // Verify file upload using helper function
    verify_file_upload(&client, "cdn/test/nested/nested.png", test_image_data);

    cleanup_test_environment();
}

#[test]
fn test_upload_special_characters() {
    // Test uploading with special characters in filename (should work)
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"special chars test";

    let response = client
        .post("/image/upload?path=test/test-file_123.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("path").unwrap().as_str().unwrap(),
        "cdn/test/test-file_123.png"
    );

    // Verify file upload using helper function
    verify_file_upload(&client, "cdn/test/test-file_123.png", test_image_data);

    cleanup_test_environment();
}

#[test]
fn test_upload_duplicate_filename() {
    // Test uploading a file with a filename that already exists
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"first upload data";

    // First upload
    let response = client
        .post("/image/upload?path=test/duplicate.png")
        .header(auth_header.clone())
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());

    // Second upload with same filename
    let second_image_data = b"second upload data";

    let response = client
        .post("/image/upload?path=test/duplicate.png")
        .header(auth_header)
        .body(second_image_data)
        .dispatch();

    // This should fail with conflict error
    assert_eq!(response.status(), Status::Conflict);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(
        body.get("error").unwrap().as_str().unwrap(),
        "File already exists"
    );

    cleanup_test_environment();
}

#[test]
fn test_upload_no_directory() {
    // Test uploading without directory parameter (should save to tests/cdn)
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let test_image_data = b"no directory test data";

    let response = client
        .post("/image/upload?path=no_dir_test.png")
        .header(auth_header)
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("path").unwrap().as_str().unwrap(),
        "cdn/no_dir_test.png"
    );

    // Verify file upload using helper function
    verify_file_upload(&client, "cdn/no_dir_test.png", test_image_data);

    cleanup_test_environment();
}
