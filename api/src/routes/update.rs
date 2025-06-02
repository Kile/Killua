use super::common::keys::ApiKey;

use serde_json::Value;

use super::common::utils::{make_request, ResultExt};
use rocket::response::status::BadRequest;
use rocket::serde::json::Json;

#[derive(FromFormField, Debug)]
pub enum TestOption {
    Pass,
    Fail,
}

struct CommandResult {
    exit_code: i32,
    output: String,
}

async fn send_command_and_get_result(
    command: String,
    first_bit: u8,
) -> Result<CommandResult, BadRequest<Json<Value>>> {
    // List files in the directory
    let response = make_request("update", command, first_bit)
        .await
        .context("Failed to get command output")?;

    let exit_code = response
        .split("\n")
        .next()
        .unwrap_or("EXIT_CODE=0")
        .to_string();
    let parsed_exit_code = exit_code
        .split('=')
        .nth(1)
        .unwrap_or("0")
        .parse::<i32>()
        .unwrap_or(0);
    let output = response
        .split("\n")
        .skip(1)
        .collect::<Vec<&str>>()
        .join("\n");

    // Remove OUTPUT= prefix if it exists
    let output = if let Some(stripped) = output.strip_prefix("OUTPUT=") {
        stripped.to_string()
    } else {
        output
    };

    Ok(CommandResult {
        exit_code: parsed_exit_code,
        output,
    })
}

#[post("/update?<force>&<test>")]
pub async fn update(
    _key: ApiKey,
    force: Option<bool>,
    test: Option<TestOption>,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    // Runs a shell script which is in scripts/update.sh
    let command = "scripts/update.sh".to_owned()
        + match test {
            Some(TestOption::Pass) => " --test-pass",
            Some(TestOption::Fail) => " --test-fail",
            None => "",
        }
        + if force.unwrap_or(false) {
            " --force"
        } else {
            ""
        };

    let output = send_command_and_get_result(command, 1_u8).await?;

    if output.exit_code != 0 {
        return Err(BadRequest(Json(
            serde_json::json!({"error": format!("Update script failed: {}", output.output)}),
        )));
    }

    Ok(Json(
        serde_json::json!({"status": format!("Success: {}", output.output)}),
    ))
}

#[options("/update")] // Sucks I have to do this
pub fn update_cors() -> Json<Value> {
    Json(serde_json::json!({
        "status": "CORS preflight request"
    }))
}
