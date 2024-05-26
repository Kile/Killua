use serde::Serialize;
use serde_json::Value;

use rocket::response::status::BadRequest;
use rocket::serde::json::Json;
use rocket::serde::Deserialize;

use super::common::keys::ApiKey;
use super::common::utils::{make_request, ResultExt};

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
// converts JSON keys to camelCase (needed for isWeekend)
#[serde(crate = "rocket::serde")]
pub struct Vote {
    user: Option<String>,
    id: Option<String>,
    is_weekend: Option<bool>,
}

#[post("/vote", data = "<vote>")]
pub async fn register_vote(
    _key: ApiKey,
    vote: Json<Vote>,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let response = make_request("vote", vote.into_inner())
        .await
        .context("Failed to register vote")?;
    // Request also failed if the response key is "error"
    if response.contains("error") {
        return Err(BadRequest(Json(serde_json::from_str(&response).unwrap_or(
            serde_json::json!({"error": "Failed to register vote"}),
        ))));
    }

    Ok(Json(serde_json::json!({"message": "Success"})))
}
