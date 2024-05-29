use mongodb::bson::DateTime;
use mongodb::Client;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::mem;
use std::sync::Mutex;

use rocket::fairing::{Fairing, Info, Kind};
use rocket::http::Status;
use rocket::{Data, Request, Response};

use crate::db::models::{ApiStats, StatsStruct};

#[derive(Serialize, Deserialize, Clone, Debug, Default)]
pub struct Endpoint {
    pub requests: Vec<i64>, // int representation of DateTime
    pub successful_responses: usize,
}

#[derive(Default, Debug)]
pub struct Counter {
    pub stats: Mutex<HashMap<String, Endpoint>>,
}

impl Counter {
    const MAX_SIZE: usize = 50;
}

fn take_if_threshold(counter: &Counter, req: &Request) -> Option<HashMap<String, Endpoint>> {
    let mut stats = counter.stats.lock().expect("poisoned lock");

    let endpoint = stats.entry(req.uri().to_string()).or_insert(Endpoint {
        requests: Vec::new(),
        successful_responses: 0,
    });
    endpoint.requests.push(DateTime::now().timestamp_millis());

    if stats
        .values()
        .map(|value| value.requests.len())
        .sum::<usize>()
        >= Counter::MAX_SIZE
    {
        Some(mem::take(&mut *stats))
    } else {
        None
    }
}

#[rocket::async_trait]
impl Fairing for Counter {
    fn info(&self) -> Info {
        Info {
            name: "GET/POST Counter",
            kind: Kind::Request | Kind::Response | Kind::Shutdown,
        }
    }

    async fn on_shutdown(&self, rocket: &rocket::Rocket<rocket::Orbit>) {
        let stats = mem::take(&mut *self.stats.lock().unwrap());
        let dbclient = rocket.state::<Client>().unwrap();
        let statsdb = ApiStats::new(dbclient);

        for (key, value) in stats.iter() {
            // Convert requests to Vec<DateTime>
            let requests: Vec<DateTime> = value
                .requests
                .iter()
                .map(|x| DateTime::from_millis(x.clone()))
                .collect();
            let stats_item = StatsStruct {
                _id: key.clone(),
                requests: requests,
                successful_responses: value.successful_responses as u32,
            };
            statsdb.update_stats(&stats_item).await;
        }
    }

    async fn on_request(&self, req: &mut Request<'_>, _: &mut Data<'_>) {
        if let Some(stats) = take_if_threshold(self, req) {
            let dbclient = req.rocket().state::<Client>().unwrap();
            let statsdb = ApiStats::new(dbclient);
            // Update the database with the current stats
            for (key, value) in stats.into_iter() {
                let statsdb = statsdb.clone();
                // "Collection uses std::sync::Arc internally, so it can safely be shared across threads or async tasks."
                // So this is ok to clone up to 50 times (like I am doin here)
                tokio::spawn(async move {
                    let requests: Vec<DateTime> = value
                        .requests
                        .iter()
                        .map(|x| DateTime::from_millis(*x))
                        .collect();
                    let stats_item = StatsStruct {
                        _id: key.clone(),
                        requests: requests,
                        successful_responses: value.successful_responses as u32,
                    };
                    statsdb.update_stats(&stats_item).await;
                });
            }
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
