use chrono::{DateTime, Utc};
use mongodb::Client;
use rocket::response::status::BadRequest;
use rocket::serde::json::Json;
use rocket::serde::{Deserialize, Serialize};
use rocket::State;
use serde_json::{json, Value};
use std::collections::HashMap;

use super::common::discord_auth::DiscordAuth;
use super::common::utils::{make_request, ResultExt};
use crate::db::models::{NewsDb, NewsType, NotifyUsers};

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct NewsResponse {
    #[serde(rename = "_id")]
    pub id: String,
    pub title: String,
    pub content: String,
    #[serde(rename = "type")]
    pub news_type: NewsType,
    pub likes: u64,
    pub liked: bool,
    pub author: AuthorInfo,
    pub version: Option<String>,
    pub published: bool,
    pub timestamp: DateTime<Utc>,
    pub links: HashMap<String, String>,
    pub images: Vec<String>,
    pub notify_users: Option<NotifyUsers>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct AuthorInfo {
    pub display_name: String,
    pub avatar_url: String,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct CreateNewsRequest {
    pub title: String,
    pub content: String,
    #[serde(rename = "type")]
    pub news_type: NewsType,
    pub version: Option<String>,
    pub published: bool,
    pub links: Option<HashMap<String, String>>,
    pub images: Option<Vec<String>>,
    pub notify_users: Option<NotifyUsers>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct EditNewsRequest {
    pub title: Option<String>,
    pub content: Option<String>,
    #[serde(rename = "type")]
    pub news_type: Option<NewsType>,
    pub version: Option<String>,
    pub published: Option<bool>,
    pub links: Option<HashMap<String, String>>,
    pub images: Option<Vec<String>>,
    pub notify_users: Option<NotifyUsers>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct NewsResponseData {
    pub news: Vec<NewsResponse>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct NewsIdRequest {
    pub news_id: String,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct LikeRequest {
    pub news_id: String,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(crate = "rocket::serde")]
pub struct NewsSaveResponse {
    pub news_id: String,
    pub message_id: Option<u64>,
}

// Get all news items
#[get("/news")]
pub async fn get_news(
    auth: Option<DiscordAuth>,
    client: &State<Client>,
) -> Result<Json<NewsResponseData>, BadRequest<Json<Value>>> {
    let news_db = NewsDb::new(client);

    let news_items = news_db.get_all_news().await.map_err(|_| {
        BadRequest(Json(
            serde_json::json!({"error": "Failed to query database"}),
        ))
    })?;

    // Sort by timestamp descending (newest first)
    let mut sorted_items = news_items;
    sorted_items.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));

    // If the user is not authenticated or if they are authenticated but not an admin, filter out drafts
    if auth.is_none() || (auth.is_some() && !auth.as_ref().unwrap().is_admin()) {
        sorted_items.retain(|item| item.published);
    }

    // Convert to response format with author info
    let mut news_responses = Vec::new();
    for item in sorted_items {
        let author_info = get_author_info(item.author).await?;

        news_responses.push(NewsResponse {
            id: item.id,
            title: item.title,
            content: item.content,
            news_type: item.news_type,
            likes: item.likes.len() as u64,
            liked: auth.as_ref().is_some_and(|a| item.likes.contains(&a.0.id)),
            author: author_info,
            version: item.version,
            published: item.published,
            timestamp: item.timestamp.to_chrono(),
            links: item.links,
            images: item.images,
            notify_users: item.notify_users,
        });
    }

    Ok(Json(NewsResponseData {
        news: news_responses,
    }))
}

// Get specific news item by ID
#[get("/news/<news_id>")]
pub async fn get_news_by_id(
    auth: Option<DiscordAuth>,
    client: &State<Client>,
    news_id: &str,
) -> Result<Json<NewsResponse>, BadRequest<Json<Value>>> {
    let news_db = NewsDb::new(client);

    let news_item = news_db
        .get_news_by_id(news_id)
        .await
        .map_err(|_| {
            BadRequest(Json(
                serde_json::json!({"error": "Failed to query database"}),
            ))
        })?
        .ok_or_else(|| BadRequest(Json(serde_json::json!({"error": "News item not found"}))))?;

    // If the user is not authenticated or if they are authenticated but not an admin, check if the item is published
    if !news_item.published
        && (auth.is_none() || (auth.is_some() && !auth.as_ref().unwrap().is_admin()))
    {
        return Err(BadRequest(Json(
            serde_json::json!({"error": "News item not found"}),
        )));
    }

    let author_info = get_author_info(news_item.author).await?;

    Ok(Json(NewsResponse {
        id: news_item.id,
        title: news_item.title,
        content: news_item.content,
        news_type: news_item.news_type,
        likes: news_item.likes.len() as u64,
        liked: auth
            .as_ref()
            .is_some_and(|a| news_item.likes.contains(&a.0.id)),
        author: author_info,
        version: news_item.version,
        published: news_item.published,
        timestamp: news_item.timestamp.to_chrono(),
        links: news_item.links,
        images: news_item.images,
        notify_users: news_item.notify_users,
    }))
}

// Like/unlike a news item
#[post("/news/like", data = "<request>")]
pub async fn like_news(
    client: &State<Client>,
    auth: DiscordAuth,
    request: Json<LikeRequest>,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let news_db = NewsDb::new(client);

    let news_item = news_db
        .get_news_by_id(&request.news_id)
        .await
        .map_err(|_| {
            BadRequest(Json(
                serde_json::json!({"error": "Failed to query database"}),
            ))
        })?
        .ok_or_else(|| BadRequest(Json(serde_json::json!({"error": "News item not found"}))))?;

    let user_id_str = auth.0.id.clone();
    let mut likes = news_item.likes.clone();

    let action = if likes.contains(&user_id_str) {
        // Unlike
        likes.retain(|id| id != &user_id_str);
        "unliked"
    } else {
        // Like
        likes.push(user_id_str);
        "liked"
    };

    // Update the database
    news_db
        .update_likes(&request.news_id, likes.clone())
        .await
        .map_err(|_| {
            BadRequest(Json(
                serde_json::json!({"error": "Failed to update database"}),
            ))
        })?;

    Ok(Json(serde_json::json!({
        "action": action,
    })))
}

// Save new news item (admin only)
#[post("/news/save", data = "<request>")]
pub async fn save_news(
    auth: DiscordAuth,
    request: Json<CreateNewsRequest>,
) -> Result<Json<NewsSaveResponse>, BadRequest<Json<Value>>> {
    // Check if user is admin
    if !auth.is_admin() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Admin access required"
        }))));
    }

    let request_data = serde_json::json!({
        "title": request.title,
        "content": request.content,
        "type": request.news_type,
        "version": request.version,
        "links": request.links,
        "images": request.images,
        "published": request.published,
        "notify_users": request.notify_users,
        "author": auth.0.id
    });

    let response = make_request("news/save", request_data, 0_u8)
        .await
        .context("Failed to save news item")?;

    let result: NewsSaveResponse = serde_json::from_str(&response).map_err(|_| {
        BadRequest(Json(
            serde_json::json!({"error": "Failed to parse response"}),
        ))
    })?;

    Ok(Json(result))
}

// Delete news item (admin only)
#[delete("/news/<news_id>")]
pub async fn delete_news(
    auth: DiscordAuth,
    news_id: &str,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    // Check if user is admin
    if !auth.is_admin() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Admin access required"
        }))));
    }

    let request_data = NewsIdRequest {
        news_id: news_id.to_string(),
    };
    let response = make_request("news/delete", request_data, 0_u8)
        .await
        .context("Failed to delete news item")?;

    let result: Value = serde_json::from_str(&response).map_err(|_| {
        BadRequest(Json(
            serde_json::json!({"error": "Failed to parse response"}),
        ))
    })?;

    Ok(Json(result))
}

// Edit news item (admin only)
#[put("/news/<news_id>", data = "<request>")]
pub async fn edit_news(
    auth: DiscordAuth,
    news_id: &str,
    request: Json<EditNewsRequest>,
) -> Result<Json<NewsSaveResponse>, BadRequest<Json<Value>>> {
    // Check if user is admin
    if !auth.is_admin() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Admin access required"
        }))));
    }

    let mut request_data = serde_json::json!({
        "news_id": news_id,
    });

    if let Some(title) = &request.title {
        request_data["title"] = json!(title);
    }
    if let Some(content) = &request.content {
        request_data["content"] = json!(content);
    }
    if let Some(news_type) = &request.news_type {
        request_data["type"] = json!(news_type);
    }
    if let Some(version) = &request.version {
        request_data["version"] = json!(version);
    }
    if let Some(published) = request.published {
        request_data["published"] = json!(published);
    }
    if let Some(links) = &request.links {
        request_data["links"] = json!(links);
    }
    if let Some(images) = &request.images {
        request_data["images"] = json!(images);
    }
    if let Some(notify_users) = &request.notify_users {
        request_data["notify_users"] = json!(notify_users);
    }

    let response = make_request("news/edit", request_data, 0_u8)
        .await
        .context("Failed to edit news item")?;

    let result: NewsSaveResponse = serde_json::from_str(&response).map_err(|_| {
        BadRequest(Json(
            serde_json::json!({"error": "Failed to parse response"}),
        ))
    })?;

    Ok(Json(result))
}

// Helper function to get author information
async fn get_author_info(author_id: i64) -> Result<AuthorInfo, BadRequest<Json<Value>>> {
    let route = "user_get_basic_details";
    let data = json!({"user_id": author_id});
    let first_bit = 0_u8;
    let response = make_request(route, data, first_bit)
        .await
        .context("Failed to get author info")?;

    let author_info: AuthorInfo = serde_json::from_str(&response).map_err(|_| {
        BadRequest(Json(
            serde_json::json!({"error": "Failed to parse response"}),
        ))
    })?;

    Ok(author_info)
}
