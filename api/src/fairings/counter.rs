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

impl Counter {
    const MAX_SIZE: usize = 50;
}

#[rocket::async_trait]
impl Fairing for Counter {
    fn info(&self) -> Info {
        Info {
            name: "GET/POST Counter",
            kind: Kind::Request | Kind::Response | Kind::Shutdown,
        }
    }

    async fn on_shutdown(&self, _: &rocket::Rocket<rocket::Orbit>) {
        let stats = self.stats.lock().expect("poisoned lock");

        db::counter::update_counter(&stats);
    }

    async fn on_request(&self, req: &mut Request<'_>, _: &mut Data<'_>) {
        let mut stats = self.stats.lock().expect("poisoned lock");

        let endpoint = stats.entry(req.uri().to_string()).or_insert(Endpoint {
            requests: 0,
            successful_responses: 0,
        });
        endpoint.requests += 1;

        if stats.values().map(|value| value.requests).sum::<usize>() >= Self::MAX_SIZE {
            db::counter::update_counter(&stats);
            stats.clear();
        }
    }

    async fn on_response<'r>(&self, req: &'r Request<'_>, res: &mut Response<'r>) {
        let status = res.status();
        if status == Status::Ok {
            let mut stats = self.stats.lock().expect("poisoned lock");

            if let Some(endpoint) = stats.get_mut(&req.uri().to_string()) {
                endpoint.successful_responses += 1;
            }
        }
    }
}
