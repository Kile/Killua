use rocket::http::Status;
use rocket::serde::json::Json;
use serde_json::{json, Value};

use super::common::discord_auth::{invalidate_token, DiscordAuth};

/// POST /logout - Invalidate the caller's cached OAuth token
#[post("/logout")]
pub fn logout(auth: DiscordAuth) -> (Status, Json<Value>) {
    invalidate_token(&auth.token);
    (Status::Ok, Json(json!({ "message": "Successfully logged out" })))
}
