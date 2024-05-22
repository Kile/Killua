use rocket::serde::{Serialize, Deserialize};
use rocket::serde::json::Json;
use std::collections::HashMap;
use std::sync::Mutex;
use serde_json::{from_str, Value};
use std::error::Error;

use crate::routes::common::make_request;

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

fn deserialize_categories(obj: HashMap<String, Value>) -> Result<HashMap<String, Category>, Box<dyn Error>> {
    obj.into_iter()
        .map(|(key, value)| {
            let category = Category {
                name: key.clone(), // Move ownership of the String
                // Deserialize the nested Value into Category
                ..Deserialize::deserialize(value)?
            };
            Ok((key.clone(), category)) // Move ownership of the String
        })
        .collect()
}

static CACHE: Mutex<Option<HashMap<String, Category>>> = Mutex::new(None);

#[get("/commands")]
pub async fn get_commands() -> Json<HashMap<String, Category>> {
    let mut cache = CACHE.lock().unwrap();
    
    if cache.is_none() {
        let commands = make_request("commands", None);
        if commands.is_err() {
            return Json(HashMap::new());
        }
        let commands = commands.unwrap();

        // Parse the commands into a HashMap using the defined structs and rocket
        let commands = (from_str::<HashMap<String, Value>>(&commands).unwrap()).clone();
        let commands = deserialize_categories(commands).unwrap();
        *cache = Some(commands);
    }
    // Get cache out of Mutex
    let cache = cache.as_ref().unwrap();
    Json(cache.clone())
}