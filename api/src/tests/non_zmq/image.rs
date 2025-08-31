use std::time::{Duration, SystemTime};

use crate::rocket;
use crate::routes::image::{sha256, HASH_SECRET};
use rocket::http::{ContentType, Status};
use rocket::local::blocking::Client;
use std::thread::sleep;

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct AllowImageResponse {
    token: String,
}

fn get_valid_token(endpoint: String, extra_secs: Option<u64>) -> (String, String) {
    let time = (SystemTime::now() + std::time::Duration::from_secs(extra_secs.unwrap_or(60)))
        .duration_since(SystemTime::UNIX_EPOCH)
        .unwrap()
        .as_secs()
        .to_string();
    (sha256(&endpoint, &time, &HASH_SECRET), time)
}

#[test]
fn get_image_without_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/image/boxes/big_box.png").dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn get_image_with_invalid_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/image/boxes/big_box.png?token=invalid_token")
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn image_does_not_exist() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, expiry) = get_valid_token("boxes/does_not_exist.png".to_string(), None);
    let response = client
        .get(format!(
            "/image/boxes/does_not_exist.png?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(response.status(), Status::NotFound);
}

#[test]
fn attempt_malice() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, expiry) = get_valid_token("Rocket.toml".to_string(), None); // Rocket will convert ../../Rocket.toml to Rocket.toml
    let response = client
        .get(format!(
            "/image/../../Rocket.toml?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(response.status(), Status::NotFound);
}

#[test]
fn get_image_with_expired_token() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, expiry) = get_valid_token("boxes/big_box.png".to_string(), Some(0));
    // Wait for the token to expire
    sleep(Duration::from_secs(1));
    let response = client
        .get(format!(
            "/image/boxes/big_box.png?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn get_single_image() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, expiry) = get_valid_token("boxes/big_box.png".to_string(), None);
    let image_response = client
        .get(format!(
            "/image/boxes/big_box.png?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
}

#[test]
fn get_single_image_with_wrong_expiry() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, _) = get_valid_token("boxes/big_box.png".to_string(), None);
    let image_response = client
        .get(format!("/image/boxes/big_box.png?token={token}&expiry=123"))
        .dispatch();
    assert_eq!(image_response.status(), Status::Forbidden);
}

#[test]
fn get_single_image_with_wrong_token() {
    let client = Client::tracked(rocket()).unwrap();
    let (_, expiry) = get_valid_token("boxes/big_box.png".to_string(), None);
    let image_response = client
        .get(format!(
            "/image/boxes/big_box.png?token=wrong_token&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(image_response.status(), Status::Forbidden);
}

#[test]
fn get_multiple_images() {
    let client = Client::tracked(rocket()).unwrap();
    let (token, expiry) = get_valid_token("vote_rewards".to_string(), None);
    let image_response = client
        .get(format!(
            "/image/boxes/big_box.png?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
    let image_response = client
        .get(format!(
            "/image/boxes/booster_box.png?token={token}&expiry={expiry}"
        ))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
}
