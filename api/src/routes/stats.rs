use rocket::serde::{Serialize, Deserialize};
use rocket::serde::json::Json;

use crate::routes::common::{make_request, NoData};

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
pub struct Stats {
    guilds: u32,
    shards: u8,
    registered_users: u32,
    last_restart: f64,
}

#[get("/stats")]
pub async fn get_stats() -> Json<Stats> {
    let stats = make_request("stats", NoData {});
    if stats.is_err() {
        return Json(Stats {
            guilds: 0,
            shards: 0,
            registered_users: 0,
            last_restart: 0.0,
        });
    }
    
    let stats = stats.unwrap();
    let stats: Stats = serde_json::from_str(&stats).unwrap();

    Json(stats)
}