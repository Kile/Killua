use serde::Serialize;
use serde_json::Value;

use rocket::serde::Deserialize;
use rocket::serde::json::Json;
use rocket::response::status::BadRequest;

use super::common::utils::{make_request, ResultExt};
use super::common::keys::ApiKey;

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
// converts JSON keys to camelCase (needed for isWeekend)
#[serde(crate = "rocket::serde")]
pub struct Vote {
    user: Option<u64>,
    id: Option<String>,
    is_weekend: Option<bool>,
}

#[post("/vote", data = "<vote>")]
pub async fn register_vote(_key: ApiKey, vote: Json<Vote>) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let response = make_request("vote", vote.into_inner()).await.context("Failed to register vote")?;
    // Request also failed if the response key is "error"
    if response.contains("error") {
        return Err(BadRequest(Json(serde_json::from_str(&response).unwrap_or(serde_json::json!({"error": "Failed to register vote"})))));
    }
    
   Ok(Json(serde_json::json!({"message": "Success"})))
}