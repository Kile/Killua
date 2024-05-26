use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::tests::common::get_key;

#[test]
fn vote_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/vote")
        .body(r#"{"user": 1, "id": "1", "isWeekend": true}"#)
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"error":"Failed to register vote"}"#
    );
}
