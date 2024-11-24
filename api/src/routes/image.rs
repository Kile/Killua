use super::common::keys::ApiKey;
use crate::db::models::ImageTokens;
use mongodb::Client;
use rocket::response::status::BadRequest;
use rocket::response::status::Forbidden;
use rocket::serde::json::Json;
use rocket::{
    fs::NamedFile,
    serde::{Deserialize, Serialize},
    State,
};
use serde_json::Value;
use std::path::{Path, PathBuf};

#[derive(Debug, Serialize, Deserialize)]
pub struct AllowImage {
    pub endpoints: Vec<String>,
}

#[get("/image/<images..>?<token>")]
pub async fn image(images: PathBuf, token: &str, client: &State<Client>) -> Option<NamedFile> {
    let tokendb = ImageTokens::new(client);
    if !tokendb
        .allows_endpoint(token, &images.to_string_lossy())
        .await
    {
        return None;
    }
    NamedFile::open(Path::new("src/images").join(images))
        .await
        .ok()
}

#[get("/image/<_images..>")]
pub async fn image_without_token(_images: PathBuf) -> Forbidden<Json<Value>> {
    Forbidden(Json(serde_json::json!({"error": "No token provided"})))
}

#[post("/allow-image", data = "<endpoints>")]
pub async fn allow_image(
    _key: ApiKey,
    endpoints: Json<AllowImage>,
    client: &State<Client>,
) -> Result<Json<Value>, BadRequest<Json<Value>>> {
    let tokendb = ImageTokens::new(client);
    let token = tokendb.generate_endpoint_token(&endpoints.endpoints).await;
    Ok(Json(serde_json::json!({"token": token})))
}
