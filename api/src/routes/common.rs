use serde::{Serialize, Deserialize};
use zmq::{Context, REQ};

#[derive(Serialize, Deserialize)]
struct RequestData<T> {
    route: String,
    data: T,
}

#[derive(Serialize, Deserialize)]
pub struct NoData {}

pub fn make_request<'a, T: Serialize + Deserialize<'a>>(route: &str, data: T) -> Result<String, zmq::Error> {
    let ctx = Context::new();
    let socket = ctx.socket(REQ).unwrap();
    
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
    assert!(socket.connect("ipc:///tmp/killua.ipc").is_ok());

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

    result?; // Return error if error (Rust is cool)
    Ok(msg.as_str().unwrap().to_string())
}