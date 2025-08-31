use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;
use serde_json::from_str;

use crate::routes::diagnostics::{DiagnosticsResponse, EndpointSummary};
use crate::tests::common::get_key;

#[test]
fn diagnostics_when_down() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    // Check the json body ipc.success is false, ignore other fields which may not be empty
    let parsed_response =
        from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();
    assert!(!parsed_response.ipc.success);
    assert_eq!(parsed_response.ipc.response_time, None);
}

#[test]
fn diagnostics_plus_one_success() {
    let client = Client::tracked(rocket()).unwrap();
    // Get initial stats
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();

    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();

    let initial_values = parsed_response.usage.clone();

    // Make a request to /stats
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::BadRequest); // This fails because the zmq server is down

    // Get stats again
    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);

    let parsed_response =
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();
    let new_values = parsed_response.usage.clone();

    // Check that the values have increased by one
    assert!(
        initial_values
            .get("/stats")
            .unwrap_or(&EndpointSummary::default())
            .request_count
            + 1
            == new_values.get("/stats").unwrap().request_count
    );
    // Request fails so the successful_responses should be the same
    assert!(
        initial_values
            .get("/stats")
            .unwrap_or(&EndpointSummary::default())
            .successful_responses
            == new_values.get("/stats").unwrap().successful_responses
    );
}
