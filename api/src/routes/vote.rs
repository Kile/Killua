use rocket::request::FromRequest;
use rocket::serde::Deserialize;
use rocket::serde::json::Json;
use serde::Serialize;
use serde_json::Value;
use rocket::response::status::BadRequest;
use rocket::tokio::task;
use rocket::request::{Request, Outcome};
use rocket::http::Status;
use rocket::State;

use crate::routes::common::make_request;
use crate::Config;

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
// converts JSON keys to camelCase (needed for isWeekend)
#[serde(crate = "rocket::serde")]
pub struct Vote {
    user: Option<u64>,
    id: Option<String>,
    is_weekend: Option<bool>,
}
pub struct ApiKey(());

#[derive(Debug)]
pub enum ApiKeyError {
    Missing,
    Invalid,
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for ApiKey {
    type Error = ApiKeyError;

    /// Returns true if `key` is a valid API key string.
    async fn from_request(req: &'r Request<'_>) -> Outcome<Self, Self::Error> {
        let config = req.guard::<&State<Config>>().await.unwrap();
        let correct_key = &config.api_key;

        match req.headers().get_one("Authorization") {
            None => Outcome::Error((Status::Forbidden, ApiKeyError::Missing)),
            Some(key) if key == correct_key => Outcome::Success(ApiKey(())),
            Some(_) => Outcome::Error((Status::Forbidden, ApiKeyError::Invalid)),
        }
    }
}

#[post("/vote", data = "<vote>")]
pub async fn register_vote(_key: ApiKey, vote: Json<Vote>) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let Ok(Ok(response)) = task::spawn_blocking(move || {
        make_request("vote", vote.into_inner())
    }).await else {
        return Err(BadRequest(Json(serde_json::json!({"error": "Failed to register vote"}))));
    };
    // Request also failed if the response key is "error"
    if response.to_string().contains("error") {
        return Err(BadRequest(Json(serde_json::from_str(&response).unwrap_or(serde_json::json!({"error": "Failed to register vote"})))));
    }
    
   Ok(Json(serde_json::json!({"message": "Success"})))
}