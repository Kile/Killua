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
use routes::discord_webhooks::{handle_discord_webhook, webhook_health_check};
use routes::guild::{
    create_tag, delete_tag, edit_guild, edit_tag, get_command_usage, get_editable_guilds,
    get_guild_info,
};
use routes::image::{delete, edit, image, list, upload};
use routes::news::{delete_news, edit_news, get_news, get_news_by_id, like_news, save_news};
use routes::stats::get_stats;
use routes::update::{update, update_cors};
use routes::user::{edit_user, edit_user_by_id, get_userinfo, get_userinfo_by_id};
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
                upload,
                delete,
                edit,
                list,
                get_diagnostics,
                get_cards,
                get_public_cards,
                update,
                update_cors,
                get_userinfo,
                get_userinfo_by_id,
                handle_discord_webhook,
                webhook_health_check,
                get_news,
                get_news_by_id,
                like_news,
                save_news,
                delete_news,
                edit_news,
                edit_user,
                edit_user_by_id,
                get_guild_info,
                edit_guild,
                get_editable_guilds,
                get_command_usage,
                create_tag,
                edit_tag,
                delete_tag,
            ],
        )
        .attach(db::init())
        .attach(Cors)
        //.manage(Arc::clone(&counter))
        //.attach(counter)
        .attach(Counter)
        .attach(RequestTimer)
}
