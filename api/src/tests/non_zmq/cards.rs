use crate::rocket;
use crate::routes::cards::{Card, parse_file};
use crate::tests::common::get_key;
use rocket::http::{ContentType, Status};
use rocket::local::blocking::Client;

#[test]
fn get_private_cards_without_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/cards.json").dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn get_private_cards_with_invalid_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/cards.json")
        .header(rocket::http::Header::new("Authorization" , "invalid_token"))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn get_private_cards() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/cards.json")
        .header(rocket::http::Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let response_string = response.into_string().unwrap();
    let cards: Vec<Card> = serde_json::from_str(&response_string).unwrap();
    let real_cards = parse_file();
    assert_eq!(cards.len(), real_cards.expect("Parsing failed").len());
}


#[test]
fn get_public_cards() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/cards.json?public=true").dispatch();
    assert_eq!(response.status(), Status::Ok);
    let response_string = response.into_string().unwrap();
    let cards: Vec<Card> = serde_json::from_str(&response_string).unwrap();
    let real_cards = parse_file();
    let real_cards_ref = real_cards.as_ref().expect("Parsing failed");
    assert_eq!(cards.len(), real_cards_ref.len());
    assert!(cards[0] != real_cards_ref[0]); // should be modified
}