use crate::rocket;
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

use crate::routes::diagnostics::{DiagnosticsFullResponse, DiagnosticsResponse, EndpointSummary};
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
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();
    assert!(parsed_response.ipc.success);
}

#[test]
fn get_diagnostics_full() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics?full=true")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsFullResponse>(&response.into_string().unwrap()).unwrap();
    assert!(parsed_response.ipc.success);
}

#[test]
fn get_diagnostics_full_false() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics?full=false")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();
    assert!(parsed_response.ipc.success);
}

#[test]
fn get_diagnostics_invalid_full_param() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get("/diagnostics?full=invalid")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    // Should default to summary format when invalid parameter is provided
    let parsed_response =
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();
    assert!(parsed_response.ipc.success);
}

#[test]
fn compare_default_vs_full_response_structure() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    // Get default response
    let default_response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(default_response.status(), Status::Ok);
    let default_data: serde_json::Value =
        serde_json::from_str(&default_response.into_string().unwrap()).unwrap();

    // Get full response
    let full_response = client
        .get("/diagnostics?full=true")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(full_response.status(), Status::Ok);
    let full_data: serde_json::Value =
        serde_json::from_str(&full_response.into_string().unwrap()).unwrap();

    // Both should have the same IPC data
    assert_eq!(default_data["ipc"]["success"], full_data["ipc"]["success"]);

    // Both should have usage data
    assert!(default_data["usage"].is_object());
    assert!(full_data["usage"].is_object());

    // Default should have request_count, full should have requests array
    if let Some(endpoint) = default_data["usage"]
        .as_object()
        .and_then(|u| u.values().next())
    {
        assert!(endpoint["request_count"].is_number());
        assert!(!endpoint.as_object().unwrap().contains_key("requests"));
    }

    if let Some(endpoint) = full_data["usage"]
        .as_object()
        .and_then(|u| u.values().next())
    {
        assert!(endpoint["requests"].is_array());
        assert!(!endpoint.as_object().unwrap().contains_key("request_count"));
    }
}

#[test]
fn verify_request_count_matches_requests_length() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();

    // Make a request to create some data
    let _ = client.get("/stats").dispatch();

    // Get full response
    let full_response = client
        .get("/diagnostics?full=true")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(full_response.status(), Status::Ok);
    let full_data: serde_json::Value =
        serde_json::from_str(&full_response.into_string().unwrap()).unwrap();

    // Get default response
    let default_response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(default_response.status(), Status::Ok);
    let default_data: serde_json::Value =
        serde_json::from_str(&default_response.into_string().unwrap()).unwrap();

    // For each endpoint, verify that request_count matches the length of requests array
    if let Some(usage) = full_data["usage"].as_object() {
        for (endpoint_name, endpoint_data) in usage {
            if let Some(requests_array) = endpoint_data["requests"].as_array() {
                let requests_length = requests_array.len();

                // Find corresponding endpoint in default response
                if let Some(default_endpoint) = default_data["usage"][endpoint_name].as_object() {
                    let request_count =
                        default_endpoint["request_count"].as_u64().unwrap() as usize;
                    assert_eq!(request_count, requests_length,
                        "Request count mismatch for endpoint {endpoint_name}: expected {requests_length}, got {request_count}");
                }
            }
        }
    }
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
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();

    let before = parsed_response.usage.get("/diagnostics").unwrap().clone();

    // Sleep for a bit to allow the stats to update
    std::thread::sleep(std::time::Duration::from_secs(1));

    let response = client
        .get("/diagnostics")
        .header(Header::new("Authorization", get_key()))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);
    let parsed_response =
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();

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
        serde_json::from_str::<DiagnosticsResponse>(&response.into_string().unwrap()).unwrap();

    let initial_values = parsed_response.usage.clone();

    // Make a request to /stats
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::Ok);

    // Sleep for a bit to allow the stats to update
    std::thread::sleep(std::time::Duration::from_secs(1));

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
    assert!(
        initial_values
            .get("/stats")
            .unwrap_or(&EndpointSummary::default())
            .successful_responses
            + 1
            == new_values.get("/stats").unwrap().successful_responses
    );
}
