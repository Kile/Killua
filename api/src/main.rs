#[macro_use] extern crate rocket;
use rocket::routes;

// add our routes and services modules
mod routes;

// import our routes
use routes::commands::get_commands;
use routes::vote::register_vote;
use routes::stats::get_stats;

#[launch]
fn rocket() -> _ {
    rocket::build().mount("/", routes![get_commands, register_vote, get_stats])
}
