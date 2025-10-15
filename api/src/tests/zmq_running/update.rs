use crate::rocket;
use crate::routes::common::discord_auth::{enable_test_mode, set_test_admin_ids};
use crate::tests::common::{test_zmq_server, INIT};
use rocket::http::Status;
use rocket::local::blocking::Client;
use std::thread;
use std::time::Duration;

#[test]
fn run_script_without_token() {
    enable_test_mode();
    set_test_admin_ids("555666777".to_string());

    let client = Client::tracked(rocket()).unwrap();
    let response = client.post("/update?test=Pass").dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn run_script_succeeding() {
    enable_test_mode();
    set_test_admin_ids("555666777".to_string());

    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    thread::sleep(Duration::from_secs(1)); // Give the thread time to start
    let response = client
        .post("/update?test=Pass")
        .header(rocket::http::Header::new(
            "Authorization",
            "Bearer admin_token",
        ))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"status":"Success: Test passed\n"}"#,
    );
}

#[test]
fn run_script_succeeding_with_force() {
    enable_test_mode();
    set_test_admin_ids("555666777".to_string());

    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/update?test=Pass&force=true")
        .header(rocket::http::Header::new(
            "Authorization",
            "Bearer admin_token",
        ))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"status":"Success: Test passed\n"}"#,
    );
}

#[test]
fn run_script_failing() {
    enable_test_mode();
    set_test_admin_ids("555666777".to_string());

    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/update?test=Fail")
        .header(rocket::http::Header::new(
            "Authorization",
            "Bearer admin_token",
        ))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"error":"Update script failed: Test failed\n"}"#,
    );
}

#[test]
fn run_script_non_admin() {
    enable_test_mode();
    set_test_admin_ids("555666777".to_string());

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .post("/update?test=Pass")
        .header(rocket::http::Header::new(
            "Authorization",
            "Bearer valid_token_1",
        ))
        .dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"error":"Access denied: Admin privileges required"}"#,
    );
}
