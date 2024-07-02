use crate::rocket;
use rocket::local::blocking::Client;
use rocket::http::Status;

#[test]
fn test_get_stats_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(response.into_string().unwrap(), r#"{"error":"Failed to get stats"}"#);
}