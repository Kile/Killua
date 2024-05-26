use rocket::request::{Request, Outcome, FromRequest};
use rocket::http::Status;
use rocket::State;

use crate::Config;

pub struct ApiKey(());

#[derive(Debug)]
pub enum ApiKeyError {
    Missing,
    Invalid,
}

#[rocket::async_trait]
impl<'r> FromRequest<'r> for ApiKey {
    type Error = ApiKeyError;

    /// Returns true if `key` is a valid API key string.
    async fn from_request(req: &'r Request<'_>) -> Outcome<Self, Self::Error> {
        let config = req.guard::<&State<Config>>().await.unwrap();
        let correct_key = &config.api_key;

        match req.headers().get_one("Authorization") {
            None => Outcome::Error((Status::Forbidden, ApiKeyError::Missing)),
            Some(key) if key == correct_key => Outcome::Success(ApiKey(())),
            Some(_) => Outcome::Error((Status::Forbidden, ApiKeyError::Invalid)),
        }
    }
}