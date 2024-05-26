use crate::rocket;
use rocket::http::Status;
use rocket::local::blocking::Client;

use crate::tests::common::{test_zmq_server, INIT};

#[test]
fn get_commands() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"CATEGORY":{"name":"category","commands":[],"description":"","emoji":{"normal":"a","unicode":"b"}}}"#
    );
}

#[test]
fn get_commands_twice() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"CATEGORY":{"name":"category","commands":[],"description":"","emoji":{"normal":"a","unicode":"b"}}}"#
    );

    // Should have cached commands so not need a zmq server to be active
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"CATEGORY":{"name":"category","commands":[],"description":"","emoji":{"normal":"a","unicode":"b"}}}"#
    );
}
