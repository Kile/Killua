use crate::rocket;
use crate::tests::common::get_key;
use crate::tests::common::{test_zmq_server, INIT};
use rocket::http::Status;
use rocket::local::blocking::Client;
use std::thread;
use std::time::Duration;

#[test]
fn run_script_without_token() {
    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/update?test=Pass").dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn run_script_succeeding() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    thread::sleep(Duration::from_secs(1)); // Give the thread time to start
    let response = client
        .post("/update?test=Pass")
        .header(rocket::http::Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"status":"Success: Test passed\n"}"#,
    );
}

#[test]
fn run_script_succeeding_with_force() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/update?test=Pass&force=true")
        .header(rocket::http::Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"status":"Success: Test passed\n"}"#,
    );
}

#[test]
fn run_script_failing() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/update?test=Fail")
        .header(rocket::http::Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"error":"Update script failed: Test failed\n"}"#,
    );
}
