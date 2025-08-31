use rocket::http::Status;
use rocket::serde::json::Json;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::routes::common::discord_auth::DiscordAuth;
use crate::routes::common::utils::make_request;

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
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ErrorResponse {
    pub error: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct UserInfoRequest {
    pub user_id: String,
    pub email: Option<String>,
}

#[get("/userinfo")]
pub async fn get_userinfo(auth: DiscordAuth) -> Result<Json<FlatUserInfoResponse>, Status> {
    // Use the authenticated user's ID
    let user_id = auth.0.id.clone();
    get_userinfo_by_id(auth, Some(&user_id)).await
}

#[get("/userinfo/<user_id>")]
pub async fn get_userinfo_by_id(
    auth: DiscordAuth,
    user_id: Option<&str>,
) -> Result<Json<FlatUserInfoResponse>, Status> {
    let is_specific_user = user_id.is_some();
    let target_user_id = user_id
        .map(|s| s.to_string())
        .unwrap_or_else(|| auth.0.id.clone());
    println!("Looking for user ID: {target_user_id}");

    // Check if the authenticated user can access this user's data
    if !auth.can_access_user(&target_user_id) {
        println!("Access denied for user: {target_user_id}");
        return Err(Status::Forbidden);
    }

    get_userinfo_by_user_id(auth, target_user_id, is_specific_user).await
}

async fn get_userinfo_by_user_id(
    auth: DiscordAuth,
    user_id: String,
    is_specific_user: bool,
) -> Result<Json<FlatUserInfoResponse>, Status> {
    println!("Looking for user with ID: {user_id}");

    // Make request to Killua bot
    // Don't send email if this is a specific user request (admin accessing other user's data)
    let email = if is_specific_user {
        None
    } else {
        auth.0.email.clone()
    };
    let request_data = UserInfoRequest { user_id, email };

    match make_request("user/info", request_data, 0_u8).await {
        Ok(response) => {
            println!("Response: {response}");
            match serde_json::from_str::<FlatUserInfoResponse>(&response) {
                Ok(user_data) => {
                    println!("Successfully retrieved user data");
                    Ok(Json(user_data))
                }
                Err(_e) => match serde_json::from_str::<ErrorResponse>(&response) {
                    Ok(error) => {
                        println!("Error: {0}", error.error);
                        Err(Status::InternalServerError)
                    }
                    Err(e) => {
                        println!("Unknown error: {e:?}");
                        Err(Status::InternalServerError)
                    }
                },
            }
        }
        Err(e) => {
            println!("Failed to get user info: {e:?}");
            Err(Status::InternalServerError)
        }
    }
}
