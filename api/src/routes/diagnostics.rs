use mongodb::bson::DateTime;
use mongodb::Client;
use std::collections::HashMap;
use std::time::SystemTime;

use rocket::response::status::BadRequest;
use rocket::serde::json::{Json, Value};
use rocket::serde::{Deserialize, Serialize};
use rocket::State;

use super::common::keys::ApiKey;
use super::common::utils::{make_request, NoData, ResultExt};
use crate::db::models::ApiStats;
use crate::fairings::counter::Endpoint;

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct IPCData {
    pub success: bool,
    pub response_time: Option<f64>,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct EndpointSummary {
    pub request_count: usize,
    pub successful_responses: usize,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct DiagnosticsResponse {
    pub usage: HashMap<String, EndpointSummary>,
    pub ipc: IPCData,
}

#[derive(Serialize, Deserialize, Default, Clone)]
pub struct DiagnosticsFullResponse {
    pub usage: HashMap<String, Endpoint>,
    pub ipc: IPCData,
}

#[get("/diagnostics?<full>")]
pub async fn get_diagnostics(
    _key: ApiKey,
    diag: &State<Client>,
    full: Option<bool>,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let diag = ApiStats::new(diag);
    let stats = diag.get_all_stats().await.context("Failed to get stats")?;
    let mut formatted: HashMap<String, Endpoint> = HashMap::new();

    for item in stats.into_iter() {
        formatted.insert(
            item._id,
            Endpoint {
                requests: item
                    .requests
                    .into_iter()
                    .map(|x| x.timestamp_millis())
                    .collect(),
                successful_responses: item.successful_responses as usize,
            },
        );
    }

    /// It is very likely that for the first time this endpoint is called,
    /// it is not yet in the database (the background task is too slow)
    /// so we need to kind of "fake" the data. This will not be a problem
    /// except for the first request
    fn insert(formatted: &mut HashMap<String, Endpoint>) {
        formatted.insert(
            "/diagnostics".to_string(),
            Endpoint {
                requests: vec![DateTime::now().timestamp_millis()],
                successful_responses: 1,
            },
        );
    }

    // Add 1 to /diagnostics successful_responses since it is not yet incremented
    match formatted.get_mut("/diagnostics") {
        Some(endpoint) => endpoint.successful_responses += 1,
        None => insert(&mut formatted),
    };
    let start_time = SystemTime::now();
    let res = make_request("heartbeat", NoData {}, 0_u8, false).await;
    let success = res.is_ok();
    let response_time = match success {
        true => Some(start_time.elapsed().unwrap().as_secs_f64() * 1000.0),
        false => None,
    };

    let ipc_data = IPCData {
        success,
        response_time,
    };

    // Return full data if ?full=true is specified
    if full.unwrap_or(false) {
        let data = DiagnosticsFullResponse {
            usage: formatted,
            ipc: ipc_data,
        };
        Ok(Json(serde_json::to_value(data).unwrap()))
    } else {
        // Return summary data with counts
        let mut summary: HashMap<String, EndpointSummary> = HashMap::new();
        for (key, endpoint) in formatted {
            summary.insert(
                key,
                EndpointSummary {
                    request_count: endpoint.requests.len(),
                    successful_responses: endpoint.successful_responses,
                },
            );
        }

        let data = DiagnosticsResponse {
            usage: summary,
            ipc: ipc_data,
        };
        Ok(Json(serde_json::to_value(data).unwrap()))
    }
}
