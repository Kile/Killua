use crate::rocket;
use mongodb::Client as MongoClient;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::Value;
use std::collections::HashMap;

use crate::db::models::NewsDb;
use crate::routes::common::discord_auth::{
    disable_test_mode, enable_test_mode, set_test_admin_ids,
};
use crate::tests::common::{test_zmq_server, INIT};

// Test fixtures
const TEST_USER_ID: &str = "123456789";
const ADMIN_USER_ID: &str = "555666777";

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
    // Enable test mode for Discord authentication
    enable_test_mode();

    // Set test admin IDs
    set_test_admin_ids(ADMIN_USER_ID.to_string());

    // Start ZMQ server
    INIT.call_once(|| {
        test_zmq_server();
    });
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

async fn create_test_news_item() {
    // Get MongoDB connection from environment
    let mongodb_uri = std::env::var("MONGODB").unwrap();

    // Try to connect to MongoDB, but don't fail if it's not available
    match MongoClient::with_uri_str(&mongodb_uri).await {
        Ok(client) => {
            let news_db = NewsDb::new(&client);

            // Create a test news item using the NewsItem struct directly
            use crate::db::models::{NewsItem, NewsType, NotifyData, NotifyType, NotifyUsers};
            use chrono::Utc;

            let test_news = NewsItem {
                id: "test_news_id".to_string(),
                title: "Test News Item".to_string(),
                content: "This is test content".to_string(),
                news_type: NewsType::News,
                likes: vec![],
                author: 123456789,
                version: None,
                message_id: None,
                published: true,
                timestamp: Utc::now().into(),
                links: HashMap::new(),
                images: vec![],
                notify_users: Some(NotifyUsers {
                    notify_type: NotifyType::Group,
                    data: NotifyData::Special("all".to_string()),
                }),
            };

            // Convert to BSON document
            let doc = mongodb::bson::to_document(&test_news).unwrap();

            if let Err(e) = news_db.collection.insert_one(doc).await {
                eprintln!("Failed to create test news item: {}", e);
            }
        }
        Err(e) => {
            eprintln!("MongoDB not available for creating test data (this is expected in some test environments): {}", e);
        }
    }
}

#[test]
fn test_save_news_success() {
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
        "version": "1.0.0",
        "published": true,
        "links": {
            "github": "https://github.com/test"
        },
        "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
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

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_save_news_unauthorized() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID); // Non-admin user

    let request_data = serde_json::json!({
        "title": "Test News Item",
        "content": "This is test content",
        "type": "news",
        "published": true,
        "links": {
            "github": "https://github.com/test"
        },
        "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
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

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_save_news_no_auth() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();

    let request_data = serde_json::json!({
        "title": "Test News Item",
        "content": "This is test content",
        "type": "news",
        "notify_users": {
            "type": "group",
            "data": "all"
        }
    });

    let response = client
        .post("/news/save")
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_get_news_success() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    // First, add some test data
    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "title": "Test News Item",
        "content": "This is test content",
        "type": "news",
        "version": "1.0.0",
        "published": true,
        "links": {
            "github": "https://github.com/test"
        },
        "images": ["https://example.com/image1.jpg", "https://example.com/image2.jpg"],
        "notify_users": {
            "type": "group",
            "data": "all"
        }
    });

    // Save a news item first
    let save_response = client
        .post("/news/save")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(save_response.status(), Status::Ok);

    // Now test getting news (should work since save succeeded)
    let response = client.get("/news").dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check response structure
    assert!(body.get("news").is_some());
    let news_array = body.get("news").unwrap().as_array().unwrap();
    // The save endpoint only calls ZMQ, it doesn't persist to database
    // So we expect an empty array unless we have test data

    // Check the first news item structure if any items exist
    if let Some(first_news) = news_array.first() {
        assert!(first_news.get("_id").is_some());
        assert!(first_news.get("title").is_some());
        assert!(first_news.get("content").is_some());
        assert!(first_news.get("type").is_some());
        assert!(first_news.get("author").is_some());
        assert!(first_news.get("likes").is_some());
        assert!(first_news.get("liked").is_some());
        assert!(first_news.get("published").is_some());
        assert!(first_news.get("timestamp").is_some());
        assert!(first_news.get("links").is_some());
        assert!(first_news.get("images").is_some());
    }

    cleanup_test_environment();
}

#[test]
fn test_get_news_by_id_success() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/news/test_news_id").dispatch();

    assert_eq!(response.status(), Status::Ok);

    let body: Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();

    // Check response structure
    assert!(body.get("_id").is_some());
    assert!(body.get("title").is_some());
    assert!(body.get("content").is_some());
    assert!(body.get("type").is_some());
    assert!(body.get("author").is_some());
    assert!(body.get("likes").is_some());
    assert!(body.get("liked").is_some());
    assert!(body.get("published").is_some());
    assert!(body.get("timestamp").is_some());
    assert!(body.get("links").is_some());
    assert!(body.get("images").is_some());

    cleanup_test_environment();
}

#[test]
fn test_get_news_by_id_not_found() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/news/nonexistent_id").dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_delete_news_success() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let response = client
        .delete("/news/test_news_id")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_delete_news_unauthorized() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID); // Non-admin user

    let response = client
        .delete("/news/test_news_id")
        .header(auth_header)
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_edit_news_success() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "title": "Updated News Item",
        "content": "This is updated content",
        "type": "update",
        "version": "2.0.0",
        "published": true,
        "links": {
            "github": "https://github.com/updated"
        },
        "notify_users": {
            "type": "group",
            "data": "voters"
        }
    });

    let response = client
        .put("/news/test_news_id")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_edit_news_unauthorized() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID); // Non-admin user

    let request_data = serde_json::json!({
        "title": "Updated News Item",
        "content": "This is updated content"
    });

    let response = client
        .put("/news/test_news_id")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}

#[test]
fn test_edit_news_publish_transition() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(ADMIN_USER_ID);

    let request_data = serde_json::json!({
        "published": true,
        "title": "Published News Item",
        "content": "This news item is being published",
        "type": "news",
        "notify_users": {
            "type": "group",
            "data": "all"
        }
    });

    let response = client
        .put("/news/test_news_id")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}
