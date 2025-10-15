use crate::rocket;
use mongodb::Client as MongoClient;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;

use crate::db::models::NewsDb;
use crate::routes::common::discord_auth::{disable_test_mode, enable_test_mode};

// Test fixtures
const ADMIN_USER_ID: &str = "555666777";

fn create_auth_header(user_id: &str) -> Header<'static> {
    // Map user IDs to the correct test tokens
    let token = match user_id {
        "555666777" => "Bearer admin_token",
        _ => "Bearer invalid_token",
    };

    Header::new("Authorization", token)
}

fn setup_test_environment() {
    // Enable test mode for Discord authentication
    enable_test_mode();
}

fn cleanup_test_environment() {
    // Disable test mode
    disable_test_mode();
}

async fn purge_news_database() {
    // Get MongoDB connection from environment
    let mongodb_uri = std::env::var("MONGODB").unwrap();

    // Try to connect to MongoDB, but don't fail if it's not available
    match MongoClient::with_uri_str(&mongodb_uri).await {
        Ok(client) => {
            let news_db = NewsDb::new(&client);
            if let Err(e) = news_db.purge_all().await {
                eprintln!("Failed to purge news database: {}", e);
            }
        }
        Err(e) => {
            eprintln!("MongoDB not available for purging (this is expected in some test environments): {}", e);
        }
    }
}

#[test]
fn test_save_news_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "title": "Test News Item",
        "content": "This is test content",
        "type": "news",
        "published": true,
        "links": {
            "github": "https://github.com/test"
        },
        "images": ["https://example.com/image1.jpg"],
        "notify_users": {
            "type": "group",
            "data": "all"
        }
    });

    let response = client
        .post("/news/save")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    // Should fail because ZMQ is down
    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());

    cleanup_test_environment();
}

#[test]
fn test_delete_news_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let response = client
        .delete("/news/test_news_id")
        .header(auth_header)
        .dispatch();

    // Should fail because ZMQ is down
    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());

    cleanup_test_environment();
}

#[test]
fn test_edit_news_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "title": "Updated Title"
    });

    let response = client
        .put("/news/test_news_id")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    // Should fail because ZMQ is down
    assert_eq!(response.status(), Status::BadRequest);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert!(body.get("error").is_some());

    cleanup_test_environment();
}

#[test]
fn test_get_news_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/news").dispatch();

    // This should still work because it uses direct database access
    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_get_news_by_id_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/news/test_id").dispatch();

    // This should still work because it uses direct database access
    // (though it might return "not found" if the ID doesn't exist)
    assert_eq!(response.status(), Status::BadRequest); // Not found

    cleanup_test_environment();
}

#[test]
fn test_like_news_zmq_down() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "news_id": "test_news_id"
    });

    let response = client
        .post("/news/like")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    // This should still work because it uses direct database access
    // (though it might return "not found" if the ID doesn't exist)
    assert_eq!(response.status(), Status::BadRequest); // Not found

    cleanup_test_environment();
}
