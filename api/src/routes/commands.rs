use rocket::serde::{Serialize, Deserialize};
use rocket::serde::json::Json;
use std::collections::HashMap;
use serde_json::{from_str, Value};
use rocket::response::status::BadRequest;
use tokio::sync::OnceCell;
use rocket::tokio::task;

use crate::routes::common::{make_request, NoData};

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
struct Emoji {
    normal: String,
    unicode: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
struct Command {
    name: String,
    description: String,
    message_usage: String,
    aliases: Vec<String>,
    cooldown: u32,
    premium_guild: bool,
    premium_user: bool,
    slash_usage: String,
}

#[derive(Serialize, Deserialize, Clone)]
#[serde(crate = "rocket::serde")]
pub struct Category{
    name: String,
    commands: Vec<Command>,
    description: String,
    emoji: Emoji,
}

static CACHE: OnceCell<HashMap<String, Category>> = OnceCell::const_new();

#[get("/commands")]
pub async fn get_commands() ->Result<Json<HashMap<String, Category>>, BadRequest<Json<Value>>> {
   let commands = CACHE.get_or_try_init(|| async {
        let Ok(Ok(commands)) = task::spawn_blocking(move || {
          make_request("commands", NoData {})
        }).await else {
            return Err(BadRequest(Json(serde_json::json!({"error": "Failed to get commands"}))));
        };
    
        // Parse the commands into a HashMap using the defined structs and rocket
        let commands = from_str::<HashMap<String, Category>>(&commands).unwrap();
    
        // the final deserialized categories to store
        Ok(commands)
    }).await;
    
    Ok(Json(commands?.clone()))
}