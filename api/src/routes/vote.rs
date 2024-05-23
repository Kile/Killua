use rocket::serde::Deserialize;
use rocket::serde::json::Json;
use serde::Serialize;
use serde_json::Value;
use rocket::response::status::BadRequest;
use rocket::tokio::task;

use crate::routes::common::make_request;

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
pub async fn register_vote(vote: Json<Vote>) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let Ok(Ok(response)) = task::spawn_blocking(move || {
        make_request("vote", vote.into_inner())
    }).await else {
        return Err(BadRequest(Json(serde_json::json!({"error": "Failed to register vote"}))));
    };
    // Request also failed if the response key is "error"
    if response.to_string().contains("error") {
        return Err(BadRequest(Json(serde_json::json!(response))));
    }
    
   Ok(Json(serde_json::json!({"message": "Success"})))
}