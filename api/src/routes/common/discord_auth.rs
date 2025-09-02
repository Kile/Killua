use rocket::http::Status;
use rocket::request::{FromRequest, Outcome, Request};
use serde::{Deserialize, Serialize};
use std::env;

// Test mode flag - set to true during tests
static TEST_MODE: std::sync::atomic::AtomicBool = std::sync::atomic::AtomicBool::new(false);
// Test admin IDs - set during tests
static TEST_ADMIN_IDS: std::sync::atomic::AtomicPtr<String> =
    std::sync::atomic::AtomicPtr::new(std::ptr::null_mut());

/// Enable test mode for Discord authentication
#[allow(dead_code)]
pub fn enable_test_mode() {
    TEST_MODE.store(true, std::sync::atomic::Ordering::Relaxed);
}

/// Disable test mode for Discord authentication
#[allow(dead_code)]
pub fn disable_test_mode() {
    TEST_MODE.store(false, std::sync::atomic::Ordering::Relaxed);
    // Clear test admin IDs
    let null_ptr = std::ptr::null_mut();
    TEST_ADMIN_IDS.store(null_ptr, std::sync::atomic::Ordering::Relaxed);
}

/// Set test admin IDs for testing
#[allow(dead_code)]
pub fn set_test_admin_ids(admin_ids: String) {
    let boxed_string = Box::new(admin_ids);
    let ptr = Box::into_raw(boxed_string);
    TEST_ADMIN_IDS.store(ptr, std::sync::atomic::Ordering::Relaxed);
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordUser {
    pub id: String,
    pub username: String,
    pub discriminator: String,
    pub avatar: Option<String>,
    pub email: Option<String>,
}

#[derive(Debug)]
pub enum DiscordAuthError {
    Missing,
    Invalid,
    DiscordApiError,
}

pub struct DiscordAuth(pub DiscordUser);

#[rocket::async_trait]
impl<'r> FromRequest<'r> for DiscordAuth {
    type Error = DiscordAuthError;

    async fn from_request(req: &'r Request<'_>) -> Outcome<Self, Self::Error> {
        // Get the Authorization header
        let auth_header = match req.headers().get_one("Authorization") {
            None => return Outcome::Error((Status::Forbidden, DiscordAuthError::Missing)),
            Some(header) => header,
        };

        // Check if it's a Bearer token
        if !auth_header.starts_with("Bearer ") {
            return Outcome::Error((Status::Forbidden, DiscordAuthError::Invalid));
        }

        // Verify the token with Discord API
        match verify_discord_token(auth_header).await {
            Ok(user) => Outcome::Success(DiscordAuth(user)),
            Err(_) => Outcome::Error((Status::Forbidden, DiscordAuthError::Invalid)),
        }
    }
}

async fn verify_discord_token(token: &str) -> Result<DiscordUser, DiscordAuthError> {
    // Check if we're in test mode
    let test_mode = TEST_MODE.load(std::sync::atomic::Ordering::Relaxed);
    if test_mode {
        return verify_discord_token_test(token);
    }

    let client = reqwest::Client::new();

    let response = client
        .get("https://discord.com/api/v10/users/@me")
        .header("Authorization", token)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                let response_text = resp.text().await.unwrap_or_default();

                match serde_json::from_str::<DiscordUser>(&response_text) {
                    Ok(user) => Ok(user),
                    Err(_e) => Err(DiscordAuthError::DiscordApiError),
                }
            } else {
                Err(DiscordAuthError::Invalid)
            }
        }
        Err(_e) => Err(DiscordAuthError::DiscordApiError),
    }
}

fn verify_discord_token_test(token: &str) -> Result<DiscordUser, DiscordAuthError> {
    // Remove "Bearer " prefix if present
    let token = if let Some(stripped) = token.strip_prefix("Bearer ") {
        stripped
    } else {
        token
    };

    match token {
        "valid_token_1" => Ok(DiscordUser {
            id: "123456789".to_string(),
            username: "testuser1".to_string(),
            discriminator: "0001".to_string(),
            avatar: Some("avatar1".to_string()),
            email: Some("user1@example.com".to_string()),
        }),
        "valid_token_2" => Ok(DiscordUser {
            id: "987654321".to_string(),
            username: "testuser2".to_string(),
            discriminator: "0002".to_string(),
            avatar: Some("avatar2".to_string()),
            email: Some("user2@example.com".to_string()),
        }),
        "admin_token" => Ok(DiscordUser {
            id: "555666777".to_string(),
            username: "adminuser".to_string(),
            discriminator: "0003".to_string(),
            avatar: Some("avatar3".to_string()),
            email: Some("admin@example.com".to_string()),
        }),
        _ => Err(DiscordAuthError::Invalid),
    }
}

impl DiscordAuth {
    /// Check if the authenticated user is an admin
    pub fn is_admin(&self) -> bool {
        let test_mode = TEST_MODE.load(std::sync::atomic::Ordering::Relaxed);

        if test_mode {
            // Use test admin IDs
            let test_admin_ids_ptr = TEST_ADMIN_IDS.load(std::sync::atomic::Ordering::Relaxed);
            if !test_admin_ids_ptr.is_null() {
                let test_admin_ids = unsafe { &*test_admin_ids_ptr };
                let admin_ids: Vec<&str> = test_admin_ids.split(',').collect();
                return admin_ids.contains(&self.0.id.as_str());
            }
        }

        // Use environment variable
        let admin_ids = env::var("ADMIN_IDS").unwrap_or_default();
        let admin_ids: Vec<&str> = admin_ids.split(',').collect();
        admin_ids.contains(&self.0.id.as_str())
    }

    /// Check if the authenticated user can access data for the given user_id
    pub fn can_access_user(&self, user_id: &str) -> bool {
        // Users can always access their own data
        if self.0.id == user_id {
            return true;
        }

        // Admins can access any user's data
        if self.is_admin() {
            return true;
        }

        false
    }
}
