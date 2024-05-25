#[macro_use] extern crate rocket;
use rocket::{routes, fairing::AdHoc};
use rocket::serde::Deserialize;

// add our routes module
mod routes;
#[cfg(test)] mod tests;

// import our routes
use routes::commands::get_commands;
use routes::vote::register_vote;
use routes::stats::get_stats;
use routes::image::image;

#[derive(Deserialize)]
#[serde(crate = "rocket::serde")]
pub struct Config {
    api_key: String,
}

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount("/", routes![get_commands, register_vote, get_stats, image])
        .attach(AdHoc::config::<Config>())
}
