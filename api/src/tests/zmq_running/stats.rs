use crate::rocket;
use rocket::http::Status;
use rocket::local::blocking::Client;

use crate::tests::common::{test_zmq_server, INIT};

#[test]
fn get_stats() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::Ok);
    let response_text = response.into_string().unwrap();
    let response_json: serde_json::Value = serde_json::from_str(&response_text).unwrap();

    // Check individual fields instead of exact string match due to JSON field ordering
    assert_eq!(response_json["guilds"], 1);
    assert_eq!(response_json["shards"], 1);
    assert_eq!(response_json["registered_users"], 1);
    assert_eq!(response_json["user_installs"], 1);
    assert_eq!(response_json["last_restart"], 1.0);
}
