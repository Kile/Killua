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

fn verify_file_not_in_list(client: &Client, expected_path: &str) {
    let auth_header = create_auth_header();
    let list_response = client.get("/image/list").header(auth_header).dispatch();
    assert_eq!(list_response.status(), Status::Ok);

    let list_body: Value = serde_json::from_str(&list_response.into_string().unwrap()).unwrap();
    let files = list_body.get("files").unwrap().as_array().unwrap();

    let expected_filename = expected_path.replace("cdn/", "");
    let file_strings: Vec<String> = files
        .iter()
        .map(|f| f.as_str().unwrap().to_string())
        .collect();

    assert!(
        !file_strings.contains(&expected_filename),
        "File {expected_filename} still found in list after deletion: {file_strings:?}"
    );
}

#[test]
fn test_delete_file() {
    // Test deleting a file
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // First upload a file to delete
    let test_image_data = b"file to delete";
    let response = client
        .post("/image/upload?path=test/delete_test.png")
        .header(auth_header.clone())
        .body(test_image_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    // Now delete the file
    let response = client
        .delete("/image/delete?path=test/delete_test.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("path").unwrap().as_str().unwrap(),
        "cdn/test/delete_test.png"
    );

    // Verify file was actually deleted
    let file_path = Path::new("../assets/cdn/test/delete_test.png");
    assert!(!file_path.exists());

    // Verify file is not in the list
    verify_file_not_in_list(&client, "cdn/test/delete_test.png");

    cleanup_test_environment();
}

#[test]
fn test_delete_file_not_found() {
    // Test deleting a file that doesn't exist
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let response = client
        .delete("/image/delete?path=nonexistent.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::NotFound);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(
        body.get("error").unwrap().as_str().unwrap(),
        "File not found"
    );

    cleanup_test_environment();
}

#[test]
fn test_delete_file_invalid_path() {
    // Test deleting with invalid path
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let response = client
        .delete("/image/delete?path=../invalid.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(body.get("error").unwrap().as_str().unwrap(), "Invalid path");

    cleanup_test_environment();
}

#[test]
fn test_edit_file() {
    // Test editing a file (rename and replace content)
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // First upload a file to edit
    let original_data = b"original content";
    let response = client
        .post("/image/upload?path=test/edit_test.png")
        .header(auth_header.clone())
        .body(original_data)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    // Now edit the file with new name
    let response = client
        .put("/image/edit?path=test/edit_test.png&new_path=test/edited_test.png")
        .header(auth_header.clone())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("old_path").unwrap().as_str().unwrap(),
        "cdn/test/edit_test.png"
    );
    assert_eq!(
        body.get("new_path").unwrap().as_str().unwrap(),
        "cdn/test/edited_test.png"
    );

    // Verify old file was deleted and new file was created with correct content
    let old_file_path = Path::new("../assets/cdn/test/edit_test.png");
    let new_file_path = Path::new("../assets/cdn/test/edited_test.png");

    assert!(!old_file_path.exists());
    assert!(new_file_path.exists());

    let saved_data = fs::read(new_file_path).unwrap();
    assert_eq!(saved_data, original_data);

    cleanup_test_environment();
}

#[test]
fn test_edit_file_not_found() {
    // Test editing a file that doesn't exist
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    let response = client
        .put("/image/edit?path=nonexistent.png&new_path=new.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::NotFound);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(
        body.get("error").unwrap().as_str().unwrap(),
        "File not found"
    );

    cleanup_test_environment();
}

#[test]
fn test_edit_file_new_name_exists() {
    // Test editing a file to a name that already exists
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // First upload two files
    let response = client
        .post("/image/upload?path=test/file1.png")
        .header(auth_header.clone())
        .body(b"file1 content")
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let response = client
        .post("/image/upload?path=test/file2.png")
        .header(auth_header.clone())
        .body(b"file2 content")
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    // Try to edit file1 to have the same name as file2
    let response = client
        .put("/image/edit?path=test/file1.png&new_path=test/file2.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Conflict);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(
        body.get("error").unwrap().as_str().unwrap(),
        "File already exists"
    );

    cleanup_test_environment();
}

#[test]
fn test_edit_file_invalid_new_filename() {
    // Test editing a file with invalid new filename
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // First upload a file
    let response = client
        .post("/image/upload?path=test/edit_test.png")
        .header(auth_header.clone())
        .body(b"content")
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    // Try to edit with invalid filename
    let response = client
        .put("/image/edit?path=test/edit_test.png&new_path=test/invalid@file.png")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(
        body.get("error").unwrap().as_str().unwrap(),
        "Invalid filename"
    );

    cleanup_test_environment();
}

#[test]
fn test_edit_directory() {
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // Create a test directory with files
    let test_dir = Path::new("../assets/cdn/test_dir");
    let file1_path = test_dir.join("file1.png");
    let file2_path = test_dir.join("file2.png");
    let subdir_path = test_dir.join("subdir");
    let file3_path = subdir_path.join("file3.png");

    fs::create_dir_all(&subdir_path).unwrap();
    fs::write(&file1_path, b"test1").unwrap();
    fs::write(&file2_path, b"test2").unwrap();
    fs::write(&file3_path, b"test3").unwrap();

    // Verify the directory and files exist
    assert!(test_dir.exists());
    assert!(file1_path.exists());
    assert!(file2_path.exists());
    assert!(subdir_path.exists());
    assert!(file3_path.exists());

    // Rename the directory
    let response = client
        .put("/image/edit?path=test_dir&new_path=renamed_dir")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("message").unwrap().as_str().unwrap(),
        "directory moved successfully"
    );
    assert_eq!(
        body.get("old_path").unwrap().as_str().unwrap(),
        "cdn/test_dir"
    );
    assert_eq!(
        body.get("new_path").unwrap().as_str().unwrap(),
        "cdn/renamed_dir"
    );

    // Verify the old directory no longer exists
    assert!(!test_dir.exists());

    // Verify the new directory and all its contents exist
    let new_dir = Path::new("../assets/cdn/renamed_dir");
    let new_file1_path = new_dir.join("file1.png");
    let new_file2_path = new_dir.join("file2.png");
    let new_subdir_path = new_dir.join("subdir");
    let new_file3_path = new_subdir_path.join("file3.png");

    assert!(new_dir.exists());
    assert!(new_file1_path.exists());
    assert!(new_file2_path.exists());
    assert!(new_subdir_path.exists());
    assert!(new_file3_path.exists());

    // Verify file contents are preserved
    let saved_data1 = fs::read(new_file1_path).unwrap();
    let saved_data2 = fs::read(new_file2_path).unwrap();
    let saved_data3 = fs::read(new_file3_path).unwrap();
    assert_eq!(saved_data1, b"test1");
    assert_eq!(saved_data2, b"test2");
    assert_eq!(saved_data3, b"test3");

    // Verify the new directory appears in the list with correct paths
    let list_auth_header = create_auth_header();
    let list_response = client
        .get("/image/list")
        .header(list_auth_header)
        .dispatch();
    assert_eq!(list_response.status(), Status::Ok);

    let list_body: Value = serde_json::from_str(&list_response.into_string().unwrap()).unwrap();
    let files = list_body.get("files").unwrap().as_array().unwrap();

    let file_strings: Vec<String> = files
        .iter()
        .map(|f| f.as_str().unwrap().to_string())
        .collect();

    assert!(file_strings.contains(&"renamed_dir/file1.png".to_string()));
    assert!(file_strings.contains(&"renamed_dir/file2.png".to_string()));
    assert!(file_strings.contains(&"renamed_dir/subdir/file3.png".to_string()));

    // Verify old paths are not in the list
    assert!(!file_strings.contains(&"test_dir/file1.png".to_string()));
    assert!(!file_strings.contains(&"test_dir/file2.png".to_string()));
    assert!(!file_strings.contains(&"test_dir/subdir/file3.png".to_string()));

    cleanup_test_environment();
}

#[test]
fn test_delete_directory() {
    setup_test_environment();

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header();

    // Create a test directory with files
    let test_dir = Path::new("../assets/cdn/test_dir");
    let file1_path = test_dir.join("file1.png");
    let file2_path = test_dir.join("file2.png");
    let subdir_path = test_dir.join("subdir");
    let file3_path = subdir_path.join("file3.png");

    fs::create_dir_all(&subdir_path).unwrap();
    fs::write(&file1_path, b"test1").unwrap();
    fs::write(&file2_path, b"test2").unwrap();
    fs::write(&file3_path, b"test3").unwrap();

    // Verify the directory and files exist
    assert!(test_dir.exists());
    assert!(file1_path.exists());
    assert!(file2_path.exists());
    assert!(subdir_path.exists());
    assert!(file3_path.exists());

    // Delete the directory
    let response = client
        .delete("/image/delete?path=test_dir")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("success").unwrap().as_bool().unwrap());
    assert_eq!(
        body.get("message").unwrap().as_str().unwrap(),
        "directory deleted successfully"
    );
    assert_eq!(body.get("path").unwrap().as_str().unwrap(), "cdn/test_dir");

    // Verify the directory and all its contents were deleted
    assert!(!test_dir.exists());
    assert!(!file1_path.exists());
    assert!(!file2_path.exists());
    assert!(!subdir_path.exists());
    assert!(!file3_path.exists());

    // Verify directory is not in the list
    verify_file_not_in_list(&client, "cdn/test_dir");

    cleanup_test_environment();
}
