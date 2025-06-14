#[macro_use]
extern crate rocket;
use rocket::routes;

// add routes module
mod db;
mod fairings;
mod routes;
#[cfg(test)]
mod tests;

// import routes
use routes::cards::{get_cards, get_public_cards};
use routes::commands::get_commands;
use routes::diagnostics::get_diagnostics;
use routes::image::image;
use routes::stats::get_stats;
use routes::update::{update, update_cors};
use routes::vote::register_vote;

use fairings::cors::Cors;
use fairings::counter::Counter;
use fairings::timer::RequestTimer;

#[launch]
fn rocket() -> _ {
    rocket::build()
        .mount(
            "/",
            routes![
                get_commands,
                register_vote,
                get_stats,
                image,
                get_diagnostics,
                get_cards,
                get_public_cards,
                update,
                update_cors,
            ],
        )
        .attach(db::init())
        .attach(Cors)
        //.manage(Arc::clone(&counter))
        //.attach(counter)
        .attach(Counter)
        .attach(RequestTimer)
}
