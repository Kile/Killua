use std::collections::HashMap;
use std::sync::Arc;
use std::time::SystemTime;

use rocket::response::status::BadRequest;
use rocket::serde::json::{Json, Value};
use rocket::serde::{Deserialize, Serialize};
use rocket::State;

use super::common::keys::ApiKey;
use super::common::utils::{make_request, NoData};
use crate::fairings::counter::{Counter, Endpoint};

#[derive(Serialize, Deserialize, Default)]
pub struct IPCData {
    pub success: bool,
    pub response_time: Option<f64>,
}

#[derive(Serialize, Deserialize, Default)]
pub struct DiagnosticsResonse {
    pub usage: HashMap<String, Endpoint>,
    pub ipc: IPCData,
}

#[get("/diagnostics")]
pub async fn get_diagnostics(
    _key: ApiKey,
    diag: &State<Arc<Counter>>,
) -> Result<Json<DiagnosticsResonse>, BadRequest<Json<Value>>> {
    let mut stats = diag.inner().stats.lock().unwrap().clone();

    // Add 1 to /diagnostics successful_responses since it is not yet incremented
    stats.get_mut("/diagnostics").unwrap().successful_responses += 1;

    let start_time = SystemTime::now();
    let res = make_request("heartbeat", NoData {}).await;
    let success = res.is_ok();
    let response_time = match success {
        true => Some(start_time.elapsed().unwrap().as_secs_f64() * 1000.0),
        false => None,
    };

    // Make new owned Counter object
    let data = DiagnosticsResonse {
        usage: stats,
        ipc: IPCData {
            success,
            response_time,
        },
    };

    Ok(Json(data))
}
