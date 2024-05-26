use crate::rocket;
use rocket::local::blocking::Client;
use rocket::http::Status;

use crate::tests::common::{INIT, test_zmq_server};


#[test]
fn get_stats() {
    INIT.call_once(|| {
        test_zmq_server();
    });

    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/stats").dispatch();
    assert_eq!(response.status(), Status::Ok);
    assert_eq!(response.into_string().unwrap(), r#"{"guilds":1,"shards":1,"registered_users":1,"last_restart":1.0}"#);
}

