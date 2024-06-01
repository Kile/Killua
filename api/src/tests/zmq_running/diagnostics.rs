use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::fairings::counter::Endpoint;
use crate::routes::diagnostics::DiagnosticsResonse;
use crate::tests::common::get_key;
use crate::tests::common::{test_zmq_server, INIT};

#[test]
fn wrong_key() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", "wrong_key"))
        .dispatch();
    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn get_diagnostics() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResonse>(&response.into_string().unwrap()).unwrap();
    assert!(parsed_response.ipc.success);
}

#[test]
fn self_success_is_accurate() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    // The success stat is applied after the code in the endpoint is called so
    // /diagnostics has to increment itself by one to be accurate
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResonse>(&response.into_string().unwrap()).unwrap();

    let before = parsed_response.usage.get("/diagnostics").unwrap().clone();

    // Sleep for a bit to allow the stats to update
    std::thread::sleep(std::time::Duration::from_secs(2));

    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResonse>(&response.into_string().unwrap()).unwrap();

    let after = parsed_response.usage.get("/diagnostics").unwrap().clone();

    assert_eq!(before.successful_responses + 1, after.successful_responses);
}

#[test]
fn diagnostics_plus_one_success() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    // Get initial stats
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();

    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResonse>(&response.into_string().unwrap()).unwrap();

    let initial_values = parsed_response.usage.clone();

    // Make a request to /stats
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::Ok);

    // Sleep for a bit to allow the stats to update
    std::thread::sleep(std::time::Duration::from_secs(2));

    // Get stats again
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);

    let parsed_response =
        serde_json::from_str::<DiagnosticsResonse>(&response.into_string().unwrap()).unwrap();
    let new_values = parsed_response.usage.clone();

    // Check that the values have increased by one
    assert!(
        initial_values
            .get("/stats")
            .unwrap_or(&Endpoint::default())
            .requests
            .len()
            + 1
            == new_values.get("/stats").unwrap().requests.len()
    );
    assert!(
        initial_values
            .get("/stats")
            .unwrap_or(&Endpoint::default())
            .successful_responses
            + 1
            == new_values.get("/stats").unwrap().successful_responses
    );
}
