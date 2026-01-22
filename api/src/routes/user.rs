use rocket::response::status::BadRequest;
use rocket::serde::json::Json;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::routes::common::discord_auth::DiscordAuth;
use crate::routes::common::utils::{make_request, ResultExt};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ActionSettings {
    pub hug: bool,
    pub cuddle: bool,
    pub pat: bool,
    pub slap: bool,
    pub poke: bool,
    pub tickle: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct EmailNotifications {
    pub news: bool,
    pub updates: bool,
    pub posts: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UserEditRequest {
    pub user_id: String,
    pub action_settings: Option<ActionSettings>,
    pub email_notifications: Option<EmailNotifications>,
    pub voting_reminder: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct UserEditPayload {
    pub action_settings: Option<ActionSettings>,
    pub email_notifications: Option<EmailNotifications>,
    pub voting_reminder: Option<bool>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UserEditResponse {
    pub success: bool,
    pub message: String,
}

// The actual response should be flat like the Python side
#[derive(Debug, Serialize, Deserialize)]
pub struct FlatUserInfoResponse {
    pub id: String,
    pub email: Option<String>,
    pub display_name: Option<String>,
    pub avatar_url: Option<String>,
    pub jenny: i32,
    pub daily_cooldown: String,
    pub met_user: Vec<String>,
    pub effects: Value,
    pub rs_cards: Vec<Vec<Value>>,
    pub fs_cards: Vec<Vec<Value>>,
    pub badges: Vec<String>,
    pub rps_stats: Value,
    pub counting_highscore: Value,
    pub trivia_stats: Value,
    pub achievements: Vec<String>,
    pub votes: i32,
    pub voting_streak: Value,
    pub voting_reminder: bool,
    pub premium_guilds: Value,
    pub lootboxes: Vec<i32>,
    pub boosters: Value,
    pub weekly_cooldown: Option<String>,
    pub action_settings: Value,
    pub action_stats: Value,
    pub locale: Option<String>,
    pub has_user_installed: bool,
    pub is_premium: bool,
    pub premium_tier: Option<String>,
    pub email_notifications: Value,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UserInfoRequest {
    pub user_id: String,
    pub email: Option<String>,
    pub from_admin: bool,
}

#[put("/user/edit", data = "<edit_data>")]
pub async fn edit_user(
    auth: DiscordAuth,
    edit_data: Json<UserEditPayload>,
) -> Result<Json<UserEditResponse>, BadRequest<Json<Value>>> {
    // Use the authenticated user's ID
    let user_id = auth.user.id.clone();
    edit_user_by_id(auth, Some(&user_id), edit_data).await
}

#[put("/user/edit/<user_id>", data = "<edit_data>")]
pub async fn edit_user_by_id(
    auth: DiscordAuth,
    user_id: Option<&str>,
    edit_data: Json<UserEditPayload>,
) -> Result<Json<UserEditResponse>, BadRequest<Json<Value>>> {
    let target_user_id = user_id
        .map(|s| s.to_string())
        .unwrap_or_else(|| auth.user.id.clone());

    // Check if the authenticated user can edit this user's data
    if !auth.can_access_user(&target_user_id) {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You can only edit your own data or be an admin to edit other users' data"
        }))));
    }

    // Create request data with parsed payload
    let request_data = UserEditRequest {
        user_id: target_user_id,
        action_settings: edit_data.action_settings.clone(),
        email_notifications: edit_data.email_notifications.clone(),
        voting_reminder: edit_data.voting_reminder,
    };

    // Check if at least one field is being edited
    if request_data.action_settings.is_none()
        && request_data.email_notifications.is_none()
        && request_data.voting_reminder.is_none()
    {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "No valid fields provided for editing. Please provide at least one of: action_settings, email_notifications, or voting_reminder"
        }))));
    }

    let response = make_request("user/edit", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to update user settings")?;

    let edit_response: UserEditResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(edit_response))
}

#[get("/user/info")]
pub async fn get_userinfo(
    auth: DiscordAuth,
) -> Result<Json<FlatUserInfoResponse>, BadRequest<Json<Value>>> {
    // Use the authenticated user's ID
    let user_id = auth.user.id.clone();
    get_userinfo_by_id(auth, Some(&user_id)).await
}

#[get("/user/info/<user_id>")]
pub async fn get_userinfo_by_id(
    auth: DiscordAuth,
    user_id: Option<&str>,
) -> Result<Json<FlatUserInfoResponse>, BadRequest<Json<Value>>> {
    let target_user_id = user_id
        .map(|s| s.to_string())
        .unwrap_or_else(|| auth.user.id.clone());

    // Check if the authenticated user can access this user's data
    if !auth.can_access_user(&target_user_id) {
        return Err(BadRequest(Json(serde_json::json!({
            "error": "Access denied: You can only access your own data or be an admin to access other users' data"
        }))));
    }

    let from_admin: bool = auth.user.id != target_user_id;
    get_userinfo_by_user_id(auth, target_user_id, from_admin).await
}

async fn get_userinfo_by_user_id(
    auth: DiscordAuth,
    user_id: String,
    from_admin: bool,
) -> Result<Json<FlatUserInfoResponse>, BadRequest<Json<Value>>> {
    // Make request to Killua bot
    // Don't send email if this is a specific user request (admin accessing other user's data)
    let email = if from_admin {
        None
    } else {
        auth.user.email.clone()
    };
    let request_data = UserInfoRequest {
        user_id,
        email,
        from_admin,
    };

    let response = make_request("user/info", request_data, 0_u8, false)
        .await
        .context("Failed to communicate with Killua bot to retrieve user information")?;

    let user_data: FlatUserInfoResponse = serde_json::from_str(&response).map_err(|e| {
        BadRequest(Json(serde_json::json!({
            "error": format!("Failed to parse user info response from Killua bot: {}", e)
        })))
    })?;

    Ok(Json(user_data))
}
