use crate::rocket;
use rocket::local::blocking::Client;
use rocket::http::{Status, ContentType};

#[test]
fn get_image() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/image/boxes/big_box.png").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.content_type(), Some(ContentType::PNG));
}

#[test]
fn get_image_error() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/image/boxes/does_not_exist.png").dispatch();
    assert_eq!(response.status(), Status::NotFound);
}

#[test]
fn attempt_malice() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/image/../../Rocket.toml").dispatch();
    assert_eq!(response.status(), Status::NotFound);
}