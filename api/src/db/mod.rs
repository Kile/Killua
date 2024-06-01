pub mod models;

use mongodb::Client;
use rocket::fairing::AdHoc;

// Tries opening config.json and reading the URI for the MongoDB database
fn get_mongo_uri() -> String {
    let config = std::fs::read_to_string("../config.json").unwrap();
    let config: serde_json::Value = serde_json::from_str(&config).unwrap();
    config["mongodb"].as_str().unwrap().to_string()
}

pub fn init() -> AdHoc {
    AdHoc::on_ignite("Connecting to MongoDB", |rocket| async {
        rocket.manage(Client::with_uri_str(get_mongo_uri()).await.unwrap())
    })
}
