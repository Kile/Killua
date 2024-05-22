use rocket::serde::Deserialize;
use rocket::serde::json::Json;
use serde::Serialize;
use serde_json::Value;

use crate::routes::common::make_request;

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
// converts JSON keys to camelCase (needed for isWeekend)
#[serde(crate = "rocket::serde")]
pub struct Vote<'r> {
    user: Option<u64>,
    id: Option<&'r str>,
    is_weekend: Option<bool>,
}

#[post("/vote", data = "<vote>")]
pub async fn register_vote(vote: Json<Vote<'_>>) -> Json<Value> {
    let response = make_request("vote", vote.into_inner());
    if response.is_err() {
        return Json(serde_json::json!({"error": "Failed to vote"}));
    }
    
   Json(serde_json::json!({"message": "Success"}))
}