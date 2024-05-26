use crate::rocket;
use rocket::http::Status;
use rocket::local::blocking::Client;

#[test]
fn get_commands_error() {
    // zmq server is down
    let client = Client::tracked(rocket()).unwrap();
    let response = client.get("/commands").dispatch();
    assert_eq!(response.status(), Status::BadRequest);
    assert_eq!(
        response.into_string().unwrap(),
        r#"{"error":"Failed to get commands"}"#
    );
}
