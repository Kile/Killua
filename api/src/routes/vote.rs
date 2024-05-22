use rocket::serde::Deserialize;
use rocket::serde::json::Json;
use std::collections::HashMap;
use serde_json::Value;

use crate::routes::common::make_request;

#[warn(non_snake_case)]
#[derive(Deserialize)]
#[serde(crate = "rocket::serde")]
pub struct Vote<'r> {
    user: Option<u64>,
    id: Option<&'r str>,
    isWeekend: Option<bool>,
}

#[post("/vote", data = "<vote>")]
pub async fn register_vote(vote: Json<Vote<'_>>) -> Json<Value> {
    let vote_data = serde_json::json!({
        "user": vote.user,
        "id": vote.id,
        "isWeekend": vote.isWeekend,
    });
    let vote_data = vote_data
        .as_object()
        .map(
            |obj| 
                obj.clone()
                .into_iter()
                .map(
                    |(k, v)| (k.to_string(), v.to_string())
                ).collect::<HashMap<String, String>>()
        );
    print!("{:?}", vote_data);
    let response = make_request("vote", vote_data);
    if response.is_err() {
        return Json(serde_json::json!({"error": "Failed to vote"}));
    }
    
   Json(serde_json::json!({"message": "Success"}))
}