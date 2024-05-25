use rocket::serde::{Serialize, Deserialize};
use rocket::serde::json::{Json, Value};
use rocket::response::status::BadRequest;
use rocket::tokio::task;

use crate::routes::common::{make_request, NoData};

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
pub struct Stats {
    pub guilds: u32,
    pub shards: u8,
    pub registered_users: u32,
    pub last_restart: f64,
}

#[get("/stats")]
pub async fn get_stats() -> Result<Json<Stats>, BadRequest<Json<Value>>> {
    let Ok(Ok(stats)) = task::spawn_blocking(move || {
        make_request("stats", NoData {})
    }).await else {
        return Err(BadRequest(Json(serde_json::json!({"error": "Failed to get stats"}))));
    };
    
    let stats: Stats = serde_json::from_str(&stats).unwrap();
    Ok(Json(stats))
}