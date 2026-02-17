use chrono::{DateTime, Utc};
use rocket::http::Status;
use rocket::request::{FromRequest, Outcome, Request};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::env;
use std::sync::RwLock;
use std::time::{Duration, Instant};

// Token cache: maps "Bearer <token>" -> CachedToken
// Guild permission cache: maps "Bearer <token>" -> CachedGuildPermissions
lazy_static::lazy_static! {
    static ref TOKEN_CACHE: RwLock<HashMap<String, CachedToken>> = RwLock::new(HashMap::new());
    static ref GUILD_PERM_CACHE: RwLock<HashMap<String, CachedGuildPermissions>> = RwLock::new(HashMap::new());
}

/// Fallback TTL used only in test mode where there is no real Discord expiry
const TEST_TOKEN_TTL: Duration = Duration::from_secs(600);

/// How long guild permission data is cached (permissions may change while token is still valid)
const GUILD_PERM_TTL: Duration = Duration::from_secs(300); // 5 minutes

/// Response from Discord's GET /oauth2/@me endpoint
#[derive(Debug, Deserialize)]
struct OAuth2MeResponse {
    expires: String,
    user: DiscordUser,
}

#[derive(Clone)]
struct CachedToken {
    user: DiscordUser,
    expires_at: Instant,
}

#[derive(Clone)]
struct CachedGuildPermissions {
    /// Guild IDs where the user has MANAGE_SERVER permission
    editable_guild_ids: Vec<i64>,
    expires_at: Instant,
}

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
    // Clear the token cache when leaving test mode
    clear_token_cache();
}

/// Set test admin IDs for testing
#[allow(dead_code)]
pub fn set_test_admin_ids(admin_ids: String) {
    let boxed_string = Box::new(admin_ids);
    let ptr = Box::into_raw(boxed_string);
    TEST_ADMIN_IDS.store(ptr, std::sync::atomic::Ordering::Relaxed);
}

#[derive(Debug, Clone, Serialize, Deserialize)]
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

pub struct DiscordAuth {
    pub user: DiscordUser,
    pub token: String, // The full "Bearer <token>" string
}

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
            Ok(user) => Outcome::Success(DiscordAuth {
                user,
                token: auth_header.to_string(),
            }),
            Err(_) => Outcome::Error((Status::Forbidden, DiscordAuthError::Invalid)),
        }
    }
}

async fn verify_discord_token(token: &str) -> Result<DiscordUser, DiscordAuthError> {
    // Check cache first (works in both test and production mode)
    if let Some(user) = get_cached_token(token) {
        return Ok(user);
    }

    // Check if we're in test mode
    let test_mode = TEST_MODE.load(std::sync::atomic::Ordering::Relaxed);

    if test_mode {
        let user = verify_discord_token_test(token)?;
        cache_token_with_expiry(token, &user, Instant::now() + TEST_TOKEN_TTL);
        return Ok(user);
    }

    // Production: call /oauth2/@me which returns user data + real token expiry
    let (user, expires_at) = verify_discord_token_prod(token).await?;
    cache_token_with_expiry(token, &user, expires_at);
    Ok(user)
}

/// Calls Discord's /oauth2/@me to verify the token and retrieve both the user
/// data and the token's actual expiry timestamp.
async fn verify_discord_token_prod(
    token: &str,
) -> Result<(DiscordUser, Instant), DiscordAuthError> {
    let client = reqwest::Client::new();

    let response = client
        .get("https://discord.com/api/v10/oauth2/@me")
        .header("Authorization", token)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                let response_text = resp.text().await.unwrap_or_default();

                match serde_json::from_str::<OAuth2MeResponse>(&response_text) {
                    Ok(oauth_resp) => {
                        let expires_at = parse_discord_expiry(&oauth_resp.expires);
                        Ok((oauth_resp.user, expires_at))
                    }
                    Err(_e) => Err(DiscordAuthError::DiscordApiError),
                }
            } else {
                Err(DiscordAuthError::Invalid)
            }
        }
        Err(_e) => Err(DiscordAuthError::DiscordApiError),
    }
}

/// Convert Discord's ISO-8601 `expires` string into a `std::time::Instant`.
fn parse_discord_expiry(expires: &str) -> Instant {
    if let Ok(expiry_dt) = expires.parse::<DateTime<Utc>>() {
        let remaining = expiry_dt
            .signed_duration_since(Utc::now())
            .to_std()
            .unwrap_or(Duration::ZERO);
        Instant::now() + remaining
    } else {
        // If parsing fails, fall back to a short TTL so we re-verify soon
        Instant::now() + Duration::from_secs(60)
    }
}

// ===== Token Cache Helpers =====

/// Look up a token in the cache, returning the user if it's present and not expired
fn get_cached_token(token: &str) -> Option<DiscordUser> {
    let cache = TOKEN_CACHE.read().ok()?;
    if let Some(cached) = cache.get(token) {
        if cached.expires_at > Instant::now() {
            return Some(cached.user.clone());
        }
    }
    None
}

/// Store a verified token with an explicit expiry instant
fn cache_token_with_expiry(token: &str, user: &DiscordUser, expires_at: Instant) {
    if let Ok(mut cache) = TOKEN_CACHE.write() {
        cache.insert(
            token.to_string(),
            CachedToken {
                user: user.clone(),
                expires_at,
            },
        );
    }
}

/// Public helper that caches with the test-mode fallback TTL (used by tests)
#[allow(dead_code)]
pub fn cache_token(token: &str, user: &DiscordUser) {
    cache_token_with_expiry(token, user, Instant::now() + TEST_TOKEN_TTL);
}

/// Remove a specific token from the cache (used by the logout endpoint)
pub fn invalidate_token(token: &str) {
    if let Ok(mut cache) = TOKEN_CACHE.write() {
        cache.remove(token);
    }
    if let Ok(mut cache) = GUILD_PERM_CACHE.write() {
        cache.remove(token);
    }
}

/// Clear all tokens and guild permissions from the cache
#[allow(dead_code)]
pub fn clear_token_cache() {
    if let Ok(mut cache) = TOKEN_CACHE.write() {
        cache.clear();
    }
    if let Ok(mut cache) = GUILD_PERM_CACHE.write() {
        cache.clear();
    }
}

/// Check if a token is currently cached (for testing)
#[allow(dead_code)]
pub fn is_token_cached(token: &str) -> bool {
    get_cached_token(token).is_some()
}

// ===== Guild Permission Cache Helpers =====

/// Look up cached guild permissions for a token
fn get_cached_guild_permissions(token: &str) -> Option<Vec<i64>> {
    let cache = GUILD_PERM_CACHE.read().ok()?;
    if let Some(cached) = cache.get(token) {
        if cached.expires_at > Instant::now() {
            return Some(cached.editable_guild_ids.clone());
        }
    }
    None
}

/// Store guild permission data in the cache
fn cache_guild_permissions(token: &str, editable_guild_ids: &[i64]) {
    if let Ok(mut cache) = GUILD_PERM_CACHE.write() {
        cache.insert(
            token.to_string(),
            CachedGuildPermissions {
                editable_guild_ids: editable_guild_ids.to_vec(),
                expires_at: Instant::now() + GUILD_PERM_TTL,
            },
        );
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

/// Permission flag for MANAGE_SERVER (1 << 5 = 32)
pub const MANAGE_SERVER: u64 = 1 << 5;

// Test guild permissions - maps user_id -> guild_id -> permissions
static TEST_GUILD_PERMISSIONS: std::sync::atomic::AtomicPtr<String> =
    std::sync::atomic::AtomicPtr::new(std::ptr::null_mut());

/// Set test guild permissions for testing
/// Format: "user_id:guild_id:permissions,user_id:guild_id:permissions,..."
#[allow(dead_code)]
pub fn set_test_guild_permissions(permissions: String) {
    let boxed_string = Box::new(permissions);
    let ptr = Box::into_raw(boxed_string);
    TEST_GUILD_PERMISSIONS.store(ptr, std::sync::atomic::Ordering::Relaxed);
}

/// Clear test guild permissions
#[allow(dead_code)]
pub fn clear_test_guild_permissions() {
    let null_ptr = std::ptr::null_mut();
    TEST_GUILD_PERMISSIONS.store(null_ptr, std::sync::atomic::Ordering::Relaxed);
}

/// Check if test mode is enabled
#[allow(dead_code)]
pub fn is_test_mode() -> bool {
    TEST_MODE.load(std::sync::atomic::Ordering::Relaxed)
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
                return admin_ids.contains(&self.user.id.as_str());
            }
        }

        // Use environment variable
        let admin_ids = env::var("ADMIN_IDS").unwrap_or_default();
        let admin_ids: Vec<&str> = admin_ids.split(',').collect();
        admin_ids.contains(&self.user.id.as_str())
    }

    /// Check if the authenticated user can access data for the given user_id
    pub fn can_access_user(&self, user_id: &str) -> bool {
        // Users can always access their own data
        if self.user.id == user_id {
            return true;
        }

        // Admins can access any user's data
        if self.is_admin() {
            return true;
        }

        false
    }

    /// Check if the authenticated user has MANAGE_SERVER permission for a guild
    /// Uses Discord API to verify permissions via the guilds endpoint
    pub async fn has_manage_server_permission(&self, guild_id: &str) -> bool {
        // Admins always have permission
        if self.is_admin() {
            return true;
        }

        // Check via Discord API
        check_guild_permission(&self.token, guild_id)
            .await
            .unwrap_or(false)
    }

    /// Get the user's ID
    pub fn get_user_id(&self) -> &str {
        &self.user.id
    }

    /// Get the auth token
    pub fn get_token(&self) -> &str {
        &self.token
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordGuildInfo {
    pub id: String,
    pub name: String,
    pub icon: Option<String>,
    pub permissions: String, // Discord returns this as a string
}

/// Check if user has MANAGE_SERVER permission for a guild via Discord API
pub async fn check_guild_permission(token: &str, guild_id: &str) -> Result<bool, DiscordAuthError> {
    // Parse guild_id as i64 and use get_editable_guilds
    let guild_id_i64: i64 = guild_id.parse().map_err(|_| DiscordAuthError::Invalid)?;
    let editable = get_editable_guilds(token, &[guild_id_i64]).await?;
    Ok(editable.contains(&guild_id_i64))
}

/// Get the list of guilds where user has MANAGE_SERVER permission
pub async fn get_editable_guilds(
    token: &str,
    guild_ids: &[i64],
) -> Result<Vec<i64>, DiscordAuthError> {
    // Check guild permission cache first
    if let Some(cached_editable) = get_cached_guild_permissions(token) {
        let filtered: Vec<i64> = cached_editable
            .into_iter()
            .filter(|id| guild_ids.contains(id))
            .collect();
        return Ok(filtered);
    }

    // Check if we're in test mode
    let test_mode = TEST_MODE.load(std::sync::atomic::Ordering::Relaxed);
    if test_mode {
        // In test mode, use the test permissions set via set_test_guild_permissions
        let user = verify_discord_token(token).await?;
        let mut editable = Vec::new();
        let test_perms_ptr = TEST_GUILD_PERMISSIONS.load(std::sync::atomic::Ordering::Relaxed);
        if !test_perms_ptr.is_null() {
            let test_perms = unsafe { &*test_perms_ptr };
            for entry in test_perms.split(',') {
                let parts: Vec<&str> = entry.split(':').collect();
                if parts.len() == 3 {
                    let test_user = parts[0];
                    let test_guild = parts[1];
                    let perms: u64 = parts[2].parse().unwrap_or(0);
                    if test_user == user.id && (perms & MANAGE_SERVER) != 0 {
                        if let Ok(guild_id) = test_guild.parse::<i64>() {
                            editable.push(guild_id);
                        }
                    }
                }
            }
        }
        // Cache the full list of editable guilds, then filter for the requested ones
        cache_guild_permissions(token, &editable);
        let filtered: Vec<i64> = editable
            .into_iter()
            .filter(|id| guild_ids.contains(id))
            .collect();
        return Ok(filtered);
    }

    let client = reqwest::Client::new();

    let response = client
        .get("https://discord.com/api/v10/users/@me/guilds")
        .header("Authorization", token)
        .send()
        .await;

    match response {
        Ok(resp) => {
            if resp.status().is_success() {
                let response_text = resp.text().await.unwrap_or_default();

                match serde_json::from_str::<Vec<DiscordGuildInfo>>(&response_text) {
                    Ok(guilds) => {
                        // Collect ALL guilds the user can manage, then cache them
                        let all_editable: Vec<i64> = guilds
                            .iter()
                            .filter_map(|guild| {
                                let guild_id = guild.id.parse::<i64>().ok()?;
                                let perms: u64 = guild.permissions.parse().unwrap_or(0);
                                if (perms & MANAGE_SERVER) != 0 {
                                    Some(guild_id)
                                } else {
                                    None
                                }
                            })
                            .collect();

                        cache_guild_permissions(token, &all_editable);

                        // Return only the requested guild IDs
                        let filtered: Vec<i64> = all_editable
                            .into_iter()
                            .filter(|id| guild_ids.contains(id))
                            .collect();
                        Ok(filtered)
                    }
                    Err(_e) => Err(DiscordAuthError::DiscordApiError),
                }
            } else {
                Err(DiscordAuthError::Invalid)
            }
        }
        Err(_e) => Err(DiscordAuthError::DiscordApiError),
    }
}
