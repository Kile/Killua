use rocket::response::status::BadRequest;
use rocket::serde::json::Json;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::routes::common::discord_auth::{
    get_editable_guilds as get_editable_guilds_api, DiscordAuth,
};
use crate::routes::common::utils::{make_request, ResultExt};

/// Error type for tag edit endpoint that can return either BadRequest or Forbidden
#[derive(Debug, Responder)]
pub enum TagEditError {
    #[response(status = 400)]
    BadRequest(Json<Value>),
    #[response(status = 403)]
    Forbidden(Json<Value>),
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildInfoRequest {
    pub guild_id: i64,
    pub user_id: i64,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TagOwner {
    pub user_id: i64,
    pub display_name: String,
    pub avatar_url: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GuildTag {
    pub name: String,
    pub created_at: String,
    pub owner: TagOwner,
    pub content: String,
    pub uses: i32,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildInfoResponse {
    pub member_count: i32,
    pub prefix: String,
    pub is_premium: bool,
    pub bot_added_on: Option<String>,
    pub tags: Vec<GuildTag>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct GuildEditPayload {
    pub prefix: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildEditRequest {
    pub guild_id: i64,
    pub user_id: i64,
    pub prefix: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildEditResponse {
    pub success: bool,
    pub message: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildEditablePayload {
    pub guild_ids: Vec<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildEditableRequest {
    pub guild_ids: Vec<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct GuildEditableResponse {
    pub editable: Vec<i64>,
    pub premium: Vec<i64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TagCreatePayload {
    pub name: String,
    pub content: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TagCreateRequest {
    pub guild_id: i64,
    pub user_id: i64,
    pub name: String,
    pub content: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TagEditPayload {
    pub name: String,
    pub content: Option<String>,
    pub new_name: Option<String>,
    pub new_owner: Option<i64>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TagEditRequest {
    pub guild_id: i64,
    pub user_id: i64,
    pub name: String,
    pub content: Option<String>,
    pub new_name: Option<String>,
    pub new_owner: Option<i64>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct TagDeletePayload {
    pub name: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TagDeleteRequest {
    pub guild_id: i64,
    pub user_id: i64,
    pub name: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct TagResponse {
    pub success: bool,
    pub message: String,
}

#[get("/guild/<guild_id>/info")]
pub async fn get_guild_info(
    auth: DiscordAuth,
    guild_id: i64,
) -> Result<Json<GuildInfoResponse>, BadRequest<Json<Value>>> {
    // Check if user has MANAGE_SERVER permission via Discord API
    if !auth
        .has_manage_server_permission(&guild_id.to_string())
        .await
    {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You need MANAGE_SERVER permission for this guild"
        }))));
    }

    // Make IPC request to get guild info from bot
    let user_id: i64 = auth.get_user_id().parse().map_err(|_| {
        BadRequest(Json(serde_json::json!({
            "error": "Invalid user ID format"
        })))
    })?;
    let request_data = GuildInfoRequest { guild_id, user_id };

    let response = make_request("guild/info", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to retrieve guild information")?;

    let guild_data: GuildInfoResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse guild info response: {}", e)
        })))
    })?;

    Ok(Json(guild_data))
}

#[post("/guild/<guild_id>/edit", data = "<edit_data>")]
pub async fn edit_guild(
    auth: DiscordAuth,
    guild_id: i64,
    edit_data: Json<GuildEditPayload>,
) -> Result<Json<GuildEditResponse>, BadRequest<Json<Value>>> {
    // Check if user has MANAGE_SERVER permission via Discord API
    if !auth
        .has_manage_server_permission(&guild_id.to_string())
        .await
    {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You need MANAGE_SERVER permission for this guild"
        }))));
    }

    // Check if at least one field is being edited
    if edit_data.prefix.is_none() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "No valid fields provided for editing. Please provide at least one of: prefix"
        }))));
    }

    // Create request data
    let user_id: i64 = auth.get_user_id().parse().map_err(|_| {
        BadRequest(Json(serde_json::json!({
            "error": "Invalid user ID format"
        })))
    })?;
    let request_data = GuildEditRequest {
        guild_id,
        user_id,
        prefix: edit_data.prefix.clone(),
    };

    let response = make_request("guild/edit", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to update guild settings")?;

    let edit_response: GuildEditResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(edit_response))
}

#[post("/guild/editable", data = "<payload>")]
pub async fn get_editable_guilds(
    auth: DiscordAuth,
    payload: Json<GuildEditablePayload>,
) -> Result<Json<GuildEditableResponse>, BadRequest<Json<Value>>> {
    // Step 1: Use Discord API to get guilds where user has MANAGE_SERVER permission
    let user_editable = get_editable_guilds_api(auth.get_token(), &payload.guild_ids)
        .await
        .map_err(|_| {
            BadRequest(Json(serde_json::json!({
                "error": "Failed to fetch guild permissions from Discord"
            })))
        })?;

    // If no guilds are editable by the user, return early
    if user_editable.is_empty() {
        return Ok(Json(GuildEditableResponse {
            editable: vec![],
            premium: vec![],
        }));
    }

    // Step 2: Make IPC request to filter by guilds the bot is actually in
    let request_data = GuildEditableRequest {
        guild_ids: user_editable,
    };

    let response = make_request("guild/editable", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to check guild membership")?;

    let bot_response: GuildEditableResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(bot_response))
}

#[post("/guild/<guild_id>/tag/create", data = "<payload>")]
pub async fn create_tag(
    auth: DiscordAuth,
    guild_id: i64,
    payload: Json<TagCreatePayload>,
) -> Result<Json<TagResponse>, BadRequest<Json<Value>>> {
    // Check if user has MANAGE_SERVER permission via Discord API
    if !auth
        .has_manage_server_permission(&guild_id.to_string())
        .await
    {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You need MANAGE_SERVER permission for this guild"
        }))));
    }

    // Validate tag name
    if payload.name.is_empty() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Tag name cannot be empty"
        }))));
    }

    let user_id: i64 = auth.get_user_id().parse().map_err(|_| {
        BadRequest(Json(serde_json::json!({
            "error": "Invalid user ID format"
        })))
    })?;
    let request_data = TagCreateRequest {
        guild_id,
        user_id,
        name: payload.name.clone(),
        content: payload.content.clone(),
    };

    let response = make_request("guild/tag/create", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to create tag")?;

    let tag_response: TagResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(tag_response))
}

#[post("/guild/<guild_id>/tag/edit", data = "<payload>")]
pub async fn edit_tag(
    auth: DiscordAuth,
    guild_id: i64,
    payload: Json<TagEditPayload>,
) -> Result<Json<TagResponse>, TagEditError> {
    // Check if user has MANAGE_SERVER permission via Discord API
    if !auth
        .has_manage_server_permission(&guild_id.to_string())
        .await
    {
        return Err(TagEditError::BadRequest(Json(serde_json::json!({
            "error": "Access denied: You need MANAGE_SERVER permission for this guild"
        }))));
    }

    // Check if at least one field is being edited
    if payload.content.is_none() && payload.new_name.is_none() && payload.new_owner.is_none() {
        return Err(TagEditError::BadRequest(Json(serde_json::json!({
            "error": "No valid fields provided for editing. Please provide at least one of: content, new_name, new_owner"
        }))));
    }

    let user_id: i64 = auth.get_user_id().parse().map_err(|_| {
        TagEditError::BadRequest(Json(serde_json::json!({
            "error": "Invalid user ID format"
        })))
    })?;
    let request_data = TagEditRequest {
        guild_id,
        user_id,
        name: payload.name.clone(),
        content: payload.content.clone(),
        new_name: payload.new_name.clone(),
        new_owner: payload.new_owner,
    };

    let response = make_request("guild/tag/edit", request_data, 0_u8, false)
        .await
        .map_err(|e| {
            TagEditError::BadRequest(Json(serde_json::json!({
                "error": format!("Failed to communicate with Killua bot to edit tag: {}", e)
            })))
        })?;

    let tag_response: TagResponse = serde_json::from_str(&response).map_err(|e| {
        TagEditError::BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    // Check if the bot returned an ownership error (for tag transfers)
    if !tag_response.success && tag_response.message.contains("not the owner") {
        return Err(TagEditError::Forbidden(Json(serde_json::json!({
            "error": tag_response.message
        }))));
    }

    Ok(Json(tag_response))
}

#[delete("/guild/<guild_id>/tag/delete", data = "<payload>")]
pub async fn delete_tag(
    auth: DiscordAuth,
    guild_id: i64,
    payload: Json<TagDeletePayload>,
) -> Result<Json<TagResponse>, BadRequest<Json<Value>>> {
    // Check if user has MANAGE_SERVER permission via Discord API
    if !auth
        .has_manage_server_permission(&guild_id.to_string())
        .await
    {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You need MANAGE_SERVER permission for this guild"
        }))));
    }

    // Validate tag name
    if payload.name.is_empty() {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Tag name cannot be empty"
        }))));
    }

    let user_id: i64 = auth.get_user_id().parse().map_err(|_| {
        BadRequest(Json(serde_json::json!({
            "error": "Invalid user ID format"
        })))
    })?;
    let request_data = TagDeleteRequest {
        guild_id,
        user_id,
        name: payload.name.clone(),
    };

    let response = make_request("guild/tag/delete", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to delete tag")?;

    let tag_response: TagResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(tag_response))
}
