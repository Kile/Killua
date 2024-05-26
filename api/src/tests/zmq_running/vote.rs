use crate::rocket;
use rocket::local::blocking::Client;
use rocket::http::{Status, Header};

use crate::tests::common::{get_key, INIT, test_zmq_server};

#[test]
fn vote() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(r#"{"user": 1, "id": "1", "isWeekend": true}"#)
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), r#"{"message":"Success"}"#);
}

#[test]
fn vote_invalid_key() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(r#"{"user": 1, "id": "1", "isWeekend": true}"#)
        .header(Header::new("Authorization", "invalid"))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn vote_missing_key() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(r#"{"user": 1, "id": "1", "isWeekend": true}"#)
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn vote_invalid_json() {    
    INIT.call_once(|| {
        test_zmq_server();
    });
    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/vote")
        .body(r#"{"user": 1, "id": "1", "isWeekend": true"#)
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
}