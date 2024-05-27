use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

use rocket::fairing::{Fairing, Info, Kind};
use rocket::http::Status;
use rocket::{Data, Request, Response};

use crate::db;

#[derive(Serialize, Deserialize, Clone, Debug, Copy, Default)]
pub struct Endpoint {
    pub requests: usize,
    pub successful_responses: usize,
}

#[derive(Default, Debug)]
pub struct Counter {
    pub stats: Mutex<HashMap<String, Endpoint>>,
}

#[rocket::async_trait]
impl Fairing for Counter {
    fn info(&self) -> Info {
        Info {
            name: "GET/POST Counter",
            kind: Kind::Request | Kind::Response,
        }
    }

    async fn on_request(&self, req: &mut Request<'_>, _: &mut Data<'_>) {
        match self.stats.lock() {
            Ok(mut stats) => {
                let endpoint = stats.entry(req.uri().to_string()).or_insert(Endpoint {
                    requests: 0,
                    successful_responses: 0,
                });
                endpoint.requests += 1;
            }
            Err(poisoned) => {
                eprintln!("Poisoned lock: {:?}", poisoned);
            }
        }
    }

    async fn on_response<'r>(&self, req: &'r Request<'_>, res: &mut Response<'r>) {
        let status = res.status();
        if status == Status::Ok {
            match self.stats.lock() {
                Ok(mut stats) => {
                    if let Some(endpoint) = stats.get_mut(&req.uri().to_string()) {
                        endpoint.successful_responses += 1;
                    }
                }
                Err(poisoned) => {
                    eprintln!("Poisoned lock: {:?}", poisoned);
                }
            }
        }
    }
}
