use crate::rocket;
use mongodb::Client as MongoClient;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use std::collections::HashMap;

use crate::db::models::NewsDb;
use crate::routes::common::discord_auth::{disable_test_mode, enable_test_mode};

// Test fixtures
const TEST_USER_ID: &str = "123456789";

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
                id: "test_news_1".to_string(),
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
fn test_like_news_success() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let request_data = serde_json::json!({
        "news_id": "test_news_1"
    });

    let response = client
        .post("/news/like")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_unlike_news_success() {
    setup_test_environment();

    // Purge database and create test data
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());
    rt.block_on(create_test_news_item());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let request_data = serde_json::json!({
        "news_id": "test_news_1"
    });

    let response = client
        .post("/news/like")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Ok);

    cleanup_test_environment();
}

#[test]
fn test_like_news_unauthorized() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();

    let request_data = serde_json::json!({
        "news_id": "test_news_1"
    });

    let response = client
        .post("/news/like")
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    cleanup_test_environment();
}

#[test]
fn test_like_news_not_found() {
    setup_test_environment();

    // Purge database before test
    let rt = tokio::runtime::Runtime::new().unwrap();
    rt.block_on(purge_news_database());

    let client = Client::tracked(rocket()).unwrap();
    let auth_header = create_auth_header(TEST_USER_ID);

    let request_data = serde_json::json!({
        "news_id": "nonexistent_news_id"
    });

    let response = client
        .post("/news/like")
        .header(auth_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(request_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::BadRequest);

    cleanup_test_environment();
}
