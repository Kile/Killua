use rocket::response::status::BadRequest;
use rocket::serde::json::{Json, Value};
use rocket::serde::{Deserialize, Serialize};

use super::common::utils::{make_request, NoData, ResultExt};

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
    let stats = make_request("stats", NoData {})
        .await
        .context("Failed to get stats")?;
    let stats: Stats = serde_json::from_str(&stats).unwrap();
    Ok(Json(stats))
}
