use std::path::{Path, PathBuf};
use rocket::fs::NamedFile;

#[get("/image/<images..>")]
pub async fn image(images: PathBuf) -> Option<NamedFile> {
    NamedFile::open(Path::new("src/images").join(images)).await.ok()
}