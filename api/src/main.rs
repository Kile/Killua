#[macro_use]
extern crate rocket;
use mongodb::Client;
use rocket::serde::Deserialize;
use rocket::{fairing::AdHoc, routes};
use std::sync::Arc;

// add routes module
mod db;
mod fairings;
mod routes;
#[cfg(test)]
mod tests;

// import routes
use routes::commands::get_commands;
use routes::diagnostics::get_diagnostics;
use routes::image::image;
use routes::stats::get_stats;
use routes::vote::register_vote;

use fairings::cors::Cors;
use fairings::counter::Counter;
use fairings::timer::RequestTimer;

use db::models::ApiStats;

#[derive(Deserialize)]
#[serde(crate = "rocket::serde")]
pub struct Config {
    api_key: String,
}
// Tries opening config.json and reading the URI for the MongoDB database
fn get_mongo_uri() -> String {
    let config = std::fs::read_to_string("../config.json").unwrap();
    let config: serde_json::Value = serde_json::from_str(&config).unwrap();
    config["mongodb"].as_str().unwrap().to_string()
}

#[rocket::main]
async fn main() -> Result<(), rocket::Error> {
    let counter = Arc::new(Counter::default());
    let client = Client::with_uri_str(get_mongo_uri()).await.unwrap();

    let _rocket = rocket::build()
        .mount(
            "/",
            routes![
                get_commands,
                register_vote,
                get_stats,
                image,
                get_diagnostics
            ],
        )
        .attach(AdHoc::config::<Config>())
        .attach(Cors)
        .manage(Arc::clone(&counter))
        .attach(counter)
        .attach(RequestTimer)
        .manage(client)
        .launch()
        .await?;

    Ok(())
}

// #[launch]
// async fn rocket() -> _ {
//     let counter = Arc::new(Counter::default());
//     let client = Client::with_uri_str(get_mongo_uri()).await.unwrap();
//     rocket::build()
//         .mount(
//             "/",
//             routes![
//                 get_commands,
//                 register_vote,
//                 get_stats,
//                 image,
//                 get_diagnostics
//             ],
//         )
//         .attach(AdHoc::config::<Config>())
//         .attach(Cors)
//         .manage(Arc::clone(&counter))
//         .attach(counter)
//         .attach(RequestTimer)
//         .manage(ApiStats::new(&client))
// }
