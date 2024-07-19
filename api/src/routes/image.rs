use rocket::fs::NamedFile;
use std::path::{Path, PathBuf};

#[get("/image/<images..>")]
pub async fn image(images: PathBuf) -> Option<NamedFile> {
    NamedFile::open(Path::new("src/images").join(images))
        .await
        .ok()
}
