use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use zmq::{Context, REQ};
use rand::{Rng, thread_rng};

#[derive(Serialize, Deserialize)]
struct RequestData {
    route: String,
    data: HashMap<String, String>,
}

pub fn make_request(route: &str, data: Option<HashMap<String, String>>) -> Result<String, zmq::Error> {
    let ctx = Context::new();
    let socket = ctx.socket(REQ).unwrap();

    // timeout after 5 seconds
    assert!(socket.set_rcvtimeo(5000).is_ok());
    assert!(socket.connect("ipc:///tmp/killua.ipc").is_ok());
    let random_identity: [u8; 32] = thread_rng().gen();
    assert!(socket.set_identity(&random_identity).is_ok());

     let request_data = RequestData {
         route: route.to_owned(),
         data: data.unwrap_or_default(),
    };

    let mut msg = zmq::Message::new();
    let request_json = serde_json::to_string(&request_data).unwrap();

    socket.send(request_json.as_bytes(), 0).unwrap();
    let result = socket.recv(&mut msg, 0);
    if result.is_err() {
        return Err(result.err().unwrap());
    }

    Ok(msg.as_str().unwrap().to_string())
}