use super::common::keys::ApiKey;
use rocket::response::status::BadRequest;
use rocket::serde::json::Json;
use rocket::serde::{Deserialize, Serialize};
use std::borrow::Cow;

use serde_json::Value;
use tokio::sync::OnceCell;

#[derive(Serialize, Deserialize, Clone, PartialEq)]
pub struct Card<'a> {
    id: u32,
    name: Cow<'a, str>,
    description: Cow<'a, str>,
    image: Cow<'a, str>,
    emoji: Cow<'a, str>,
    rank: Cow<'a, str>,
    limit: u32,
    r#type: Cow<'a, str>,
    available: bool,
}

static CENSORED_CACHE: OnceCell<Json<Vec<Card<'static>>>> = OnceCell::const_new();
static CACHE: OnceCell<Json<Vec<Card<'static>>>> = OnceCell::const_new();

pub fn parse_file() -> Result<Vec<Card<'static>>, BadRequest<Json<Value>>> {
    let cards = include_str!("../cards.json");
    let cards: Vec<Card<'static>> = match serde_json::from_str(cards) {
        Ok(cards) => cards,
        Err(_) => {
            warn!("Failed to parse cards.json");
            return Err(BadRequest(Json(serde_json::json!({
                "error": "Failed to parse cards.json"
            }))));
        }
    };
    Ok(cards)
}

#[get("/cards.json")]
pub async fn get_cards(_key: ApiKey) -> Result<Json<Vec<Card<'static>>>, BadRequest<Json<Value>>> {
    CACHE
        .get_or_try_init(|| async {
            let cards = parse_file()?;
            Ok(Json(cards))
        })
        .await
        .cloned()
}

#[get("/cards.json?public=true")]
pub async fn get_public_cards() -> Result<Json<Vec<Card<'static>>>, BadRequest<Json<Value>>> {
    CENSORED_CACHE.get_or_try_init(|| async {
        let cards = parse_file()?;
        // Censor the description, emoji and image
        let cards = cards.into_iter().map(|mut card| {
            if card.id == 0 {
                card.name = Cow::Borrowed("[REDACTED]");
            }
            card.description = Cow::Borrowed("Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat");
            card.emoji = Cow::Borrowed("<:badge_one_star_hunter:788935576836374548>");
            card.image = match card.r#type {
                ref t if t == &Cow::Borrowed("normal") => if card.id < 100 {Cow::Borrowed("/image/cards/PLACEHOLDER_RESTRICTED_SLOT.png")} else {Cow::Borrowed("/image/cards/PLACEHOLDER_NORMAL.png")},
                ref t if t ==&Cow::Borrowed("spell") => Cow::Borrowed("/image/cards/PLACEHOLDER_SPELL.png"),
                ref t if t == &Cow::Borrowed("ruler") => Cow::Borrowed("/image/cards/PLACEHOLDER_RULER.png"),
                ref t if t == &Cow::Borrowed("monster") => Cow::Borrowed("/image/cards/PLACEHOLDER_NORMAL.png"),
                _ => Cow::Borrowed("/image/cards/PLACEHOLDER_NORMAL.png")
            };
            card
        }).collect();
        Ok(Json(cards))
    }).await.cloned()
}
