use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use tokio::task;
use zmq::{Context, SocketType::DEALER};

use rocket::response::status::BadRequest;
use rocket::serde::json::Json;

pub trait ResultExt<T> {
    fn context(self, message: &str) -> Result<T, BadRequest<Json<Value>>>;
}
impl<T, E> ResultExt<T> for Result<T, E> {
    fn context(self, message: &str) -> Result<T, BadRequest<Json<Value>>> {
        self.map_err(|_| BadRequest(Json(json!({ "error": message }))))
    }
}

#[derive(Serialize, Deserialize)]
struct RequestData<T> {
    route: String,
    data: T,
}

#[derive(Serialize, Deserialize)]
pub struct NoData {}

pub fn make_request_inner<'a, T: Serialize + Deserialize<'a>>(
    route: &str,
    data: T,
    first_bit: u8,
) -> Result<String, zmq::Error> {
    let ctx = Context::new();
    let socket = ctx.socket(DEALER).unwrap();

    assert!(socket.set_linger(0).is_ok());
    // Omg this function...
    // I have spent EIGHT MONTHS trying to first
    // trouble shoot why i need this function, then
    // when rewriting the API finding what it is called.
    // Without this, the memory will not get dropped
    // when the client is killed (in rust when an error happens),
    // leading to the API requesting it never responding
    // and silently timing out without error.
    // What a nightmare to debug.
    // I am so glad I am done with this. (thanks y21)

    // Here are the docs why this happens
    // https://libzmq.readthedocs.io/en/zeromq3-x/zmq_setsockopt.html

    // timeout
    assert!(socket.set_rcvtimeo(5000).is_ok());
    assert!(socket.set_sndtimeo(1000).is_ok());
    assert!(socket.set_connect_timeout(5000).is_ok());
    // Get route from environment variable
    let address = std::env::var("ZMQ_ADDRESS").unwrap_or("tcp://0.0.0.0:3210".to_string());
    assert!(socket.connect(&address).is_ok());
    assert!(socket.set_identity("api-client".as_bytes()).is_ok());

    let request_data = RequestData {
        route: route.to_owned(),
        data,
    };

    let mut msg = zmq::Message::new();
    let request_json = serde_json::to_string(&request_data).unwrap();

    let mut data = vec![first_bit];
    data.extend_from_slice(request_json.as_bytes());
    socket.send("", zmq::SNDMORE)?; // delimiter
    socket.send(data, 0)?;

    socket.recv(&mut msg, 0)?; // Receive acknowledgment from the server

    // Close the socket
    assert!(socket.disconnect(&address).is_ok());

    Ok(msg.as_str().unwrap_or("").to_string())
}

pub async fn make_request<T: Serialize + std::marker::Send + Deserialize<'static> + 'static>(
    route: &'static str,
    data: T,
    first_bit: u8,
) -> Result<String, zmq::Error> {
    task::spawn_blocking(move || make_request_inner(route, data, first_bit))
        .await
        .unwrap()
}
