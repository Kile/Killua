use regex::RegexSet;
use rocket::response::status::Forbidden;
use rocket::serde::json::Json;
use rocket::{
    fs::NamedFile,
    serde::{Deserialize, Serialize},
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::SystemTime;

lazy_static::lazy_static! {
    pub static ref HASH_SECRET: String = std::env::var("HASH_SECRET").unwrap();
    static ref REGEX_SET: RegexSet = RegexSet::new([
        r"cards/.*",
        r"misc/(book_default.png|book_first.png)",
        r"(boxes/.*|powerups/logo.png)"
    ]).unwrap();
    static ref SPECIAL_ENDPOINT_MAPPING: HashMap<usize, String> =
    [
        (0, "all_cards".to_string()),
        (1, "book".to_string()),
        (2, "vote_rewards".to_string())
    ].iter().cloned().collect();
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AllowImage {
    pub endpoints: Vec<String>,
}

pub fn sha256(endpoint: &str, expiry: &str, secret: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(format!("{}{}{}", endpoint, expiry, secret));
    format!("{:x}", hasher.finalize())
}

/// Check if the token is valid and has not expired as well as if the
/// endpoint is allowed and the time has not expired
fn allows_endpoint(token: &str, endpoint: &str, expiry: &str) -> bool {
    // If the expiry is in the past, the token is invalid
    if expiry.parse::<u64>().unwrap()
        < SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs()
    {
        return false;
    }
    sha256(endpoint, expiry, &HASH_SECRET) == token
        || REGEX_SET.matches(endpoint).iter().any(|x| {
            sha256(
                SPECIAL_ENDPOINT_MAPPING.get(&x).unwrap(),
                expiry,
                &HASH_SECRET,
            ) == token
        })
}

#[get("/image/<images..>?<token>&<expiry>")]
pub async fn image(
    images: PathBuf,
    token: Option<&str>,
    expiry: Option<&str>,
) -> Result<Option<NamedFile>, Forbidden<Json<Value>>> {
    if token.is_none() || expiry.is_none() {
        return Err(Forbidden(Json(
            serde_json::json!({"error": "No token or expiry provided"}),
        )));
    }
    if !allows_endpoint(token.unwrap(), &images.to_string_lossy(), expiry.unwrap()) {
        return Err(Forbidden(Json(
            serde_json::json!({"error": "Invalid token"}),
        )));
    };
    Ok(NamedFile::open(Path::new("src/images").join(images))
        .await
        .ok())
}
