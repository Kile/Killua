use crate::rocket;
use crate::routes::image::AllowImage;
use crate::tests::common::get_key;
use rocket::http::{ContentType, Status};
use rocket::local::blocking::Client;

#[derive(Debug, serde::Serialize, serde::Deserialize)]
struct AllowImageResponse {
    token: String,
}

fn get_valid_token(client: &Client, endpoints: Vec<String>) -> String {
    let response = client
        .post("/allow-image")
        .header(ContentType::JSON)
        .header(rocket::http::Header::new("Authorization", get_key()))
        .body(serde_json::to_string(&AllowImage { endpoints }).unwrap())
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let response_string = response.into_string().unwrap();
    serde_json::from_str::<AllowImageResponse>(&response_string)
        .unwrap()
        .token
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
    let parsed_token = get_valid_token(&client, vec!["boxes/does_not_exist.png".to_string()]);
    let response = client
        .get(format!(
            "/image/boxes/does_not_exist.png?token={}",
            parsed_token
        ))
        .dispatch();
    assert_eq!(response.status(), Status::NotFound);
}

#[test]
fn attempt_malice() {
    let client = Client::tracked(rocket()).unwrap();
    let parsed_token = get_valid_token(&client, vec!["Rocket.toml".to_string()]); // Rocket will convert ../../Rocket.toml to Rocket.toml
    let response = client
        .get(format!("/image/../../Rocket.toml?token={}", parsed_token))
        .dispatch();
    assert_eq!(response.status(), Status::NotFound);
}

#[test]
fn allow_image_wrong_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/allow-image")
        .header(ContentType::JSON)
        .header(rocket::http::Header::new("Authorization", "wrong_key"))
        .body(serde_json::to_string(&AllowImage { endpoints: vec![] }).unwrap())
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn allow_single_image() {
    let client = Client::tracked(rocket()).unwrap();
    let parsed_token = get_valid_token(&client, vec!["boxes/big_box.png".to_string()]);
    let image_response = client
        .get(format!("/image/boxes/big_box.png?token={}", parsed_token))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
}

#[test]
fn allow_multiple_images() {
    let client = Client::tracked(rocket()).unwrap();
    let parsed_token = get_valid_token(
        &client,
        vec![
            "boxes/big_box.png".to_string(),
            "boxes/booster_box.png".to_string(),
        ],
    );
    let image_response = client
        .get(format!("/image/boxes/big_box.png?token={}", parsed_token))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
    let image_response = client
        .get(format!(
            "/image/boxes/booster_box.png?token={}",
            parsed_token
        ))
        .dispatch();
    assert_eq!(image_response.status(), Status::Ok);
    assert_eq!(image_response.content_type(), Some(ContentType::PNG));
}
