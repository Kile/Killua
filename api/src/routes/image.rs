use regex::Regex;
use regex::RegexSet;
use rocket::data::ToByteUnit;
use rocket::response::status::Forbidden;
use rocket::serde::json::Json;
use rocket::{
    fs::NamedFile,
    serde::{Deserialize, Serialize},
    Data,
};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::time::SystemTime;
use tokio::fs;
use tokio::io::AsyncWriteExt;

use crate::routes::common::discord_auth::DiscordAuth;

// Common validation functions
fn validate_filename(filename: &str) -> Result<(), (rocket::http::Status, Json<Value>)> {
    let filename_regex = Regex::new(r"^[a-zA-Z0-9._-]+$").unwrap();
    if filename.is_empty() || !filename_regex.is_match(filename) {
        return Err((
            rocket::http::Status::BadRequest,
            Json(serde_json::json!({"error": "Invalid filename"})),
        ));
    }
    Ok(())
}

fn validate_path(path: &str) -> Result<(), (rocket::http::Status, Json<Value>)> {
    if path.is_empty() || path.contains("..") || path.contains("\\") {
        return Err((
            rocket::http::Status::BadRequest,
            Json(serde_json::json!({"error": "Invalid path"})),
        ));
    }
    Ok(())
}

fn check_file_exists(file_path: &Path) -> Result<(), (rocket::http::Status, Json<Value>)> {
    if !file_path.exists() {
        return Err((
            rocket::http::Status::NotFound,
            Json(serde_json::json!({"error": "File not found"})),
        ));
    }
    Ok(())
}

fn check_file_not_exists(file_path: &Path) -> Result<(), (rocket::http::Status, Json<Value>)> {
    if file_path.exists() {
        return Err((
            rocket::http::Status::Conflict,
            Json(serde_json::json!({"error": "File already exists"})),
        ));
    }
    Ok(())
}

fn extract_filename_from_path(path: &str) -> Result<&str, (rocket::http::Status, Json<Value>)> {
    let path_parts: Vec<&str> = path.split('/').collect();
    let filename = path_parts.last().ok_or((
        rocket::http::Status::BadRequest,
        Json(serde_json::json!({"error": "Invalid path"})),
    ))?;
    Ok(filename)
}

lazy_static::lazy_static! {
    pub static ref HASH_SECRET: String = std::env::var("HASH_SECRET").unwrap_or_else(|_| "test_secret_key".to_string());
    static ref REGEX_SET: RegexSet = RegexSet::new([
        r"cards/.*",
        r"misc/(book_default.png|book_first.png)",
        r"(boxes/.*|powerups/logo.png)",
        r"cdn/.*"
    ]).unwrap();
    static ref SPECIAL_ENDPOINT_MAPPING: HashMap<usize, String> =
    [
        (0, "all_cards".to_string()),
        (1, "book".to_string()),
        (2, "vote_rewards".to_string()),
        (3, "cdn".to_string()),
    ].iter().cloned().collect();
}

#[derive(Debug, Serialize, Deserialize)]
pub struct AllowImage {
    pub endpoints: Vec<String>,
}

pub fn sha256(endpoint: &str, expiry: &str, secret: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(format!("{endpoint}{expiry}{secret}"));
    format!("{:x}", hasher.finalize())
}

/// Check if the token is valid and has not expired as well as if the
/// endpoint is allowed and the time has not expired
fn allows_endpoint(token: &str, endpoint: &str, expiry: &str) -> bool {
    // If the expiry is in the past, the token is invalid
    if expiry.parse::<u64>().unwrap()
        < SystemTime::now()
            .duration_since(SystemTime::UNIX_EPOCH)
            .unwrap()
            .as_secs()
    {
        return false;
    }
    sha256(endpoint, expiry, &HASH_SECRET) == token
        || REGEX_SET.matches(endpoint).iter().any(|x| {
            sha256(
                SPECIAL_ENDPOINT_MAPPING.get(&x).unwrap(),
                expiry,
                &HASH_SECRET,
            ) == token
        })
}

#[get("/image/<images..>?<token>&<expiry>")]
pub async fn image(
    images: PathBuf,
    token: Option<&str>,
    expiry: Option<&str>,
) -> Result<Option<NamedFile>, Forbidden<Json<Value>>> {
    if token.is_none() || expiry.is_none() {
        return Err(Forbidden(Json(
            serde_json::json!({"error": "No token or expiry provided"}),
        )));
    }
    if !allows_endpoint(token.unwrap(), &images.to_string_lossy(), expiry.unwrap()) {
        return Err(Forbidden(Json(
            serde_json::json!({"error": "Invalid token"}),
        )));
    };
    Ok(NamedFile::open(Path::new("../assets").join(images))
        .await
        .ok())
}

#[post("/image/upload?<path>", data = "<data>")]
pub async fn upload(
    auth: DiscordAuth,
    data: Data<'_>,
    path: Option<&str>,
) -> Result<Json<Value>, (rocket::http::Status, Json<Value>)> {
    // Check if user is admin
    if !auth.is_admin() {
        return Err((
            rocket::http::Status::Forbidden,
            Json(serde_json::json!({"error": "Admin access required"})),
        ));
    }

    // Validate required parameters
    let path = match path {
        Some(p) => p.trim_matches('/'),
        None => {
            return Err((
                rocket::http::Status::BadRequest,
                Json(serde_json::json!({"error": "Path parameter is required"})),
            ));
        }
    };

    // Validate path to prevent directory traversal attacks
    validate_path(path)?;

    // Extract and validate filename
    let filename = extract_filename_from_path(path)?;
    validate_filename(filename)?;

    // Create the full file path
    let file_path = Path::new("../assets/cdn").join(path);

    // Check if file already exists
    check_file_not_exists(&file_path)?;

    // Ensure the directory exists
    let cdn_path = if path.contains('/') {
        file_path.parent().unwrap()
    } else {
        Path::new("../assets/cdn")
    };
    if fs::create_dir_all(&cdn_path).await.is_err() {
        return Err((
            rocket::http::Status::InternalServerError,
            Json(serde_json::json!({"error": "Failed to create directory"})),
        ));
    }

    // Read the uploaded data
    let bytes = match data.open(10.mebibytes()).into_bytes().await {
        Ok(bytes) => bytes,
        Err(_) => {
            return Err((
                rocket::http::Status::BadRequest,
                Json(serde_json::json!({"error": "Failed to read uploaded data"})),
            ));
        }
    };

    // Write the file
    let mut file = match fs::File::create(&file_path).await {
        Ok(file) => file,
        Err(_) => {
            return Err((
                rocket::http::Status::InternalServerError,
                Json(serde_json::json!({"error": "Failed to create file"})),
            ));
        }
    };

    if file.write_all(&bytes).await.is_err() {
        return Err((
            rocket::http::Status::InternalServerError,
            Json(serde_json::json!({"error": "Failed to write file"})),
        ));
    }

    Ok(Json(serde_json::json!({
        "success": true,
        "message": "File uploaded successfully",
        "path": format!("cdn/{}", path)
    })))
}

#[delete("/image/delete?<path>")]
pub async fn delete(
    auth: DiscordAuth,
    path: Option<&str>,
) -> Result<Json<Value>, (rocket::http::Status, Json<Value>)> {
    // Check admin authorization
    if !auth.is_admin() {
        return Err((
            rocket::http::Status::Forbidden,
            Json(serde_json::json!({"error": "Admin authorization required"})),
        ));
    }

    // Validate required parameters
    let path = match path {
        Some(p) => p.trim_matches('/'),
        None => {
            return Err((
                rocket::http::Status::BadRequest,
                Json(serde_json::json!({"error": "Path parameter is required"})),
            ));
        }
    };

    // Validate path to prevent directory traversal attacks
    validate_path(path)?;

    // Create the full file path
    let file_path = Path::new("../assets/cdn").join(path);

    // Check if file exists and is actually a file
    check_file_exists(&file_path)?;

    // Delete the file or directory
    let is_directory = file_path.is_dir();
    let result = if is_directory {
        fs::remove_dir_all(&file_path).await
    } else {
        fs::remove_file(&file_path).await
    };

    match result {
        Ok(_) => {
            let item_type = if is_directory { "directory" } else { "file" };
            Ok(Json(serde_json::json!({
                "success": true,
                "message": format!("{} deleted successfully", item_type),
                "path": format!("cdn/{}", path)
            })))
        },
        Err(_) => {
            let item_type = if is_directory { "directory" } else { "file" };
            Err((
                rocket::http::Status::InternalServerError,
                Json(serde_json::json!({"error": format!("Failed to delete {}", item_type)})),
            ))
        }
    }
}

#[put("/image/edit?<path>&<new_path>")]
pub async fn edit(
    auth: DiscordAuth,
    path: Option<&str>,
    new_path: Option<&str>,
) -> Result<Json<Value>, (rocket::http::Status, Json<Value>)> {
    // Check admin authorization
    if !auth.is_admin() {
        return Err((
            rocket::http::Status::Forbidden,
            Json(serde_json::json!({"error": "Admin authorization required"})),
        ));
    }

    // Validate required parameters
    let path = match path {
        Some(p) => p.trim_matches('/'),
        None => {
            return Err((
                rocket::http::Status::BadRequest,
                Json(serde_json::json!({"error": "Path parameter is required"})),
            ));
        }
    };

    let new_path = match new_path {
        Some(p) => p.trim_matches('/'),
        None => {
            return Err((
                rocket::http::Status::BadRequest,
                Json(serde_json::json!({"error": "New path parameter is required"})),
            ));
        }
    };

    // Validate paths to prevent directory traversal attacks
    validate_path(path)?;
    validate_path(new_path)?;

    // Create the full file paths
    let old_file_path = Path::new("../assets/cdn").join(path);
    let new_file_path = Path::new("../assets/cdn").join(new_path);

    // Check if old path exists
    check_file_exists(&old_file_path)?;

    // Determine if we're dealing with a directory or file
    let is_directory = old_file_path.is_dir();

    if is_directory {
        // For directories, we need to validate the new directory name
        // Extract the directory name from the new path
        let new_dir_name = new_path.split('/').last().unwrap_or(new_path);
        validate_filename(new_dir_name)?;
    } else {
        // For files, validate the new filename as before
        let new_filename = extract_filename_from_path(new_path)?;
        validate_filename(new_filename)?;
    }

    // Check if new path already exists
    check_file_not_exists(&new_file_path)?;

    // Ensure the directory for the new path exists
    let new_dir_path = new_file_path.parent().unwrap();
    if fs::create_dir_all(&new_dir_path).await.is_err() {
        return Err((
            rocket::http::Status::InternalServerError,
            Json(serde_json::json!({"error": "Failed to create directory for new path"})),
        ));
    }

    // Move the file or directory (rename operation)
    if fs::rename(&old_file_path, &new_file_path).await.is_err() {
        let item_type = if is_directory { "directory" } else { "file" };
        return Err((
            rocket::http::Status::InternalServerError,
            Json(serde_json::json!({"error": format!("Failed to move {}", item_type)})),
        ));
    }

    let item_type = if is_directory { "directory" } else { "file" };
    Ok(Json(serde_json::json!({
        "success": true,
        "message": format!("{} moved successfully", item_type),
        "old_path": format!("cdn/{}", path),
        "new_path": format!("cdn/{}", new_path)
    })))
}

#[get("/image/list")]
pub async fn list(auth: DiscordAuth) -> Result<Json<Value>, (rocket::http::Status, Json<Value>)> {
    // Check admin authorization
    if !auth.is_admin() {
        return Err((
            rocket::http::Status::Forbidden,
            Json(serde_json::json!({"error": "Admin authorization required"})),
        ));
    }

    let cdn_path = Path::new("../assets/cdn");

    // Check if cdn directory exists
    if !cdn_path.exists() {
        return Ok(Json(serde_json::json!({
            "success": true,
            "files": []
        })));
    }

    // Collect all files recursively
    let mut files = Vec::new();
    if collect_files_recursively(cdn_path, &mut files, cdn_path).is_err() {
        return Err((
            rocket::http::Status::InternalServerError,
            Json(serde_json::json!({"error": "Failed to read directory"})),
        ));
    }

    // Sort files for consistent output
    files.sort();

    Ok(Json(serde_json::json!({
        "success": true,
        "files": files
    })))
}

fn collect_files_recursively(
    dir_path: &Path,
    files: &mut Vec<String>,
    base_path: &Path,
) -> Result<(), std::io::Error> {
    if !dir_path.is_dir() {
        return Ok(());
    }

    for entry in std::fs::read_dir(dir_path)? {
        let entry = entry?;
        let path = entry.path();

        if path.is_file() {
            // Convert to relative path from base_path
            let relative_path = path.strip_prefix(base_path).unwrap();
            files.push(relative_path.to_string_lossy().to_string());
        } else if path.is_dir() {
            collect_files_recursively(&path, files, base_path)?;
        }
    }

    Ok(())
}
