pub mod models;

use mongodb::Client;
use rocket::fairing::AdHoc;

// Tries opening config.json and reading the URI for the MongoDB database
fn get_mongo_uri() -> String {
    // Read environment variable
    std::env::var("MONGODB").unwrap()
}

pub fn init() -> AdHoc {
    AdHoc::on_ignite("Connecting to MongoDB", |rocket| async {
        rocket.manage(Client::with_uri_str(get_mongo_uri()).await.unwrap())
    })
}
