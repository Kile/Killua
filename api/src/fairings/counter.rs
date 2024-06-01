use mongodb::Client;
use serde::{Deserialize, Serialize};

use rocket::fairing::{Fairing, Info, Kind};
use rocket::http::Status;
use rocket::{Data, Request, Response};

use crate::db::models::ApiStats;

#[derive(Serialize, Deserialize, Clone, Debug, Default)]
pub struct Endpoint {
    pub requests: Vec<i64>, // int representation of DateTime
    pub successful_responses: usize,
}

#[derive(Default, Debug)]
pub struct Counter;

/// Parse the endpoint to turn endpoints like /image/folder/image.png into
/// just /image
fn parse_endpoint(rocket: &rocket::Rocket<rocket::Orbit>, endpoint: String) -> String {
    let all_endpoints = rocket.routes();
    // If and endpoint starts with endpoint, return the startswith part
    for route in all_endpoints {
        if route.name.is_none() {
            continue;
        }
        if endpoint.starts_with(&("/".to_owned() + route.name.as_ref().unwrap().as_ref())) {
            return "/".to_owned() + route.name.as_ref().unwrap().as_ref();
        }
    }

    endpoint
}

#[rocket::async_trait]
impl Fairing for Counter {
    fn info(&self) -> Info {
        Info {
            name: "GET/POST Counter",
            kind: Kind::Request | Kind::Response | Kind::Shutdown,
        }
    }

    async fn on_request(&self, req: &mut Request<'_>, _: &mut Data<'_>) {
        let dbclient = req.rocket().state::<Client>().unwrap();
        let statsdb = ApiStats::new(dbclient);
        let id = parse_endpoint(req.rocket(), req.uri().path().to_string());
        // Update the database with the current stats
        tokio::spawn(async move {
            statsdb.add_request(&id).await;
        });
    }

    async fn on_response<'r>(&self, req: &'r Request<'_>, res: &mut Response<'r>) {
        let status = res.status();
        if status == Status::Ok {
            let dbclient = req.rocket().state::<Client>().unwrap();
            let statsdb = ApiStats::new(dbclient);
            let id = parse_endpoint(req.rocket(), req.uri().path().to_string());
            // Update the database with the current stats
            tokio::spawn(async move {
                statsdb.add_successful_response(&id).await;
            });
        }
    }
}
