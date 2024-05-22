use serde::{Serialize, Deserialize};
use zmq::{Context, REQ};
use rand::{Rng, thread_rng};

#[derive(Serialize, Deserialize)]
struct RequestData<T>
{
    route: String,
    data: T,
}

#[derive(Serialize, Deserialize)]
pub struct NoData {}

pub fn make_request<'a, T: Serialize + Deserialize<'a>>(route: &str, data: T) -> Result<String, zmq::Error> {
    let ctx = Context::new();
    let socket = ctx.socket(REQ).unwrap();

    // timeout after 5 seconds
    assert!(socket.set_rcvtimeo(5000).is_ok());
    assert!(socket.connect("ipc:///tmp/killua.ipc").is_ok());
    let random_identity: [u8; 32] = thread_rng().gen();
    assert!(socket.set_identity(&random_identity).is_ok());

     let request_data = RequestData {
         route: route.to_owned(),
         data,
    };

    let mut msg = zmq::Message::new();
    let request_json = serde_json::to_string(&request_data).unwrap();

    socket.send(request_json.as_bytes(), 0).unwrap();
    let result = socket.recv(&mut msg, 0);

    // Close the socket
    assert!(socket.disconnect("ipc:///tmp/killua.ipc").is_ok());
    if result.is_err() {
        return Err(result.err().unwrap());
    }

    Ok(msg.as_str().unwrap().to_string())
}