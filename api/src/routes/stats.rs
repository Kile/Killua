use rocket::serde::{Serialize, Deserialize};
use rocket::serde::json::Json;

use crate::routes::common::make_request;

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
struct Stats {
    guilds: u32,
    shards: u8,
    registered_users: u32,
    last_restart: f64,
}

// {"guilds": len(self.client.guilds), "shards": self.client.shard_count, "registered_users": DB.teams.count_documents({}), "last_restart": self.client.startup_datetime.timestamp()}

#[get("/stats")]
pub async fn get_stats() -> Json<Stats> {
    
    let stats = make_request("stats", None);
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