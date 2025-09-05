use rocket::http::Status;
use rocket::response::status;
use rocket::response::Responder;
use rocket::serde::json::Json;
use serde::{Deserialize, Serialize};
use serde_json::Value;

use crate::routes::common::discord_security::{verify_discord_signature, OptionalDiscordSignature};
use crate::routes::common::utils::make_request;

// Discord webhook event types
#[derive(Debug, Serialize, Deserialize)]
pub enum DiscordEventType {
    #[serde(rename = "APPLICATION_AUTHORIZED")]
    ApplicationAuthorized,
    #[serde(rename = "APPLICATION_DEAUTHORIZED")]
    ApplicationDeauthorized,
}

// Discord user object structure
#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordUser {
    pub id: String,
    pub username: String,
    pub discriminator: Option<String>,
    pub avatar: Option<String>,
    pub bot: Option<bool>,
    pub system: Option<bool>,
    pub mfa_enabled: Option<bool>,
    pub banner: Option<String>,
    pub accent_color: Option<i32>,
    pub locale: Option<String>,
    pub verified: Option<bool>,
    pub email: Option<String>,
    pub flags: Option<i32>,
    pub premium_type: Option<i32>,
    pub public_flags: Option<i32>,
}

// Discord guild object structure
#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordGuild {
    pub id: String,
    pub name: String,
    pub icon: Option<String>,
    pub icon_hash: Option<String>,
    pub splash: Option<String>,
    pub discovery_splash: Option<String>,
    pub owner: Option<bool>,
    pub owner_id: Option<String>,
    pub permissions: Option<String>,
    pub region: Option<String>,
    pub afk_channel_id: Option<String>,
    pub afk_timeout: Option<i32>,
    pub widget_enabled: Option<bool>,
    pub widget_channel_id: Option<String>,
    pub verification_level: Option<i32>,
    pub default_message_notifications: Option<i32>,
    pub explicit_content_filter: Option<i32>,
    pub roles: Option<Vec<Value>>,
    pub emojis: Option<Vec<Value>>,
    pub features: Option<Vec<String>>,
    pub mfa_level: Option<i32>,
    pub application_id: Option<String>,
    pub system_channel_id: Option<String>,
    pub system_channel_flags: Option<i32>,
    pub rules_channel_id: Option<String>,
    pub max_presences: Option<i32>,
    pub max_members: Option<i32>,
    pub vanity_url_code: Option<String>,
    pub description: Option<String>,
    pub banner: Option<String>,
    pub premium_tier: Option<i32>,
    pub premium_subscription_count: Option<i32>,
    pub preferred_locale: Option<String>,
    pub public_updates_channel_id: Option<String>,
    pub max_video_channel_users: Option<i32>,
    pub approximate_member_count: Option<i32>,
    pub approximate_presence_count: Option<i32>,
    pub welcome_screen: Option<Value>,
    pub nsfw_level: Option<i32>,
    pub stickers: Option<Vec<Value>>,
    pub premium_progress_bar_enabled: Option<bool>,
}

// Application Authorized event data
#[derive(Debug, Serialize, Deserialize)]
pub struct ApplicationAuthorizedData {
    pub integration_type: Option<i32>, // 0 for guild, 1 for user
    pub user: DiscordUser,
    pub scopes: Vec<String>,
    pub guild: Option<DiscordGuild>,
}

// Application Deauthorized event data
#[derive(Debug, Serialize, Deserialize)]
pub struct ApplicationDeauthorizedData {
    pub user: DiscordUser,
}

// Discord webhook event structure
#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordWebhookEvent {
    pub version: i32,
    pub application_id: String,
    #[serde(rename = "type")]
    pub event_type: i32,
    pub event: Option<DiscordEvent>,
}

// Individual event structure
#[derive(Debug, Serialize, Deserialize)]
pub struct DiscordEvent {
    #[serde(rename = "type")]
    pub event_type: Option<DiscordEventType>,
    #[serde(default)]
    pub timestamp: Option<String>,
    pub data: Option<Value>, // Will be deserialized based on event type, None for ping events
}

// Request structures for forwarding to Killua bot
#[derive(Debug, Serialize, Deserialize)]
pub struct ApplicationAuthorizedRequest {
    pub application_id: String,
    pub integration_type: Option<i32>,
    pub user: DiscordUser,
    pub scopes: Vec<String>,
    pub guild: Option<DiscordGuild>,
    pub timestamp: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApplicationDeauthorizedRequest {
    pub application_id: String,
    pub user: DiscordUser,
    pub timestamp: String,
}

// Response structure
#[derive(Debug)]
pub enum WebhookResponseType {
    Json(Json<WebhookResponse>),
    NoContent,
}

impl<'r> Responder<'r, 'static> for WebhookResponseType {
    fn respond_to(self, request: &'r rocket::Request<'_>) -> rocket::response::Result<'static> {
        match self {
            WebhookResponseType::Json(json) => json.respond_to(request),
            WebhookResponseType::NoContent => status::NoContent.respond_to(request),
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WebhookResponse {
    pub success: bool,
    pub message: String,
}

#[post("/webhooks/discord", data = "<webhook_data>")]
pub async fn handle_discord_webhook(
    signature: OptionalDiscordSignature,
    webhook_data: Json<DiscordWebhookEvent>,
) -> Result<WebhookResponseType, Status> {
    // Get the webhook data and body for signature verification
    let webhook = webhook_data.into_inner();

    // Check if this is a ping event (no event field)
    let is_ping_event = webhook.event.is_none();

    // For non-ping events, require authentication
    if !is_ping_event && !signature.is_authenticated {
        return Err(Status::Unauthorized);
    }

    // For authenticated events (non-ping), verify the signature
    if signature.is_authenticated && !is_ping_event {
        eprintln!("=== DISCORD WEBHOOK HANDLER DEBUG ===");
        eprintln!("DEBUG: Processing authenticated webhook request");
        eprintln!("DEBUG: Webhook data: {:?}", webhook);

        let public_key = match std::env::var("PUBLIC_KEY") {
            Ok(key) => {
                eprintln!("DEBUG: PUBLIC_KEY environment variable found");
                key
            }
            Err(_) => {
                // Log the error for debugging
                eprintln!("ERROR: PUBLIC_KEY environment variable not set");
                return Err(Status::InternalServerError);
            }
        };

        let signature_str = signature.signature.as_ref().unwrap();
        let timestamp_str = signature.timestamp.as_ref().unwrap();
        let body = serde_json::to_string(&webhook).unwrap();

        eprintln!("DEBUG: Calling verify_discord_signature with:");
        eprintln!("  Public key: {}", public_key);
        eprintln!("  Signature: {}", signature_str);
        eprintln!("  Timestamp: {}", timestamp_str);
        eprintln!("  Body: {}", body);

        if !verify_discord_signature(&public_key, signature_str, timestamp_str, &body) {
            // Log the error for debugging
            eprintln!("ERROR: Discord signature verification failed - returning 403 Forbidden");
            return Err(Status::Forbidden);
        }

        eprintln!("DEBUG: Discord signature verification succeeded");
        eprintln!("=== END DISCORD WEBHOOK HANDLER DEBUG ===");
    }

    match webhook.event.as_ref().and_then(|e| e.event_type.as_ref()) {
        Some(DiscordEventType::ApplicationAuthorized) => {
            handle_application_authorized(webhook).await
        }
        Some(DiscordEventType::ApplicationDeauthorized) => {
            handle_application_deauthorized(webhook).await
        }
        None => {
            // This is a ping event (no event field) - Discord requires empty body and 204 status
            Ok(WebhookResponseType::NoContent)
        }
    }
}

async fn handle_application_authorized(
    webhook: DiscordWebhookEvent,
) -> Result<WebhookResponseType, Status> {
    // Parse the event data
    let event = webhook.event.ok_or(Status::BadRequest)?;
    let data = event.data.ok_or(Status::BadRequest)?;
    let event_data: ApplicationAuthorizedData =
        serde_json::from_value(data).map_err(|_| Status::BadRequest)?;

    let request_data = ApplicationAuthorizedRequest {
        application_id: webhook.application_id,
        integration_type: event_data.integration_type,
        user: event_data.user,
        scopes: event_data.scopes,
        guild: event_data.guild,
        timestamp: event.timestamp.unwrap_or_default(),
    };

    if request_data.integration_type != Some(1) {
        // we only care about user integrations
        return Ok(WebhookResponseType::Json(Json(WebhookResponse {
            success: true,
            message: "Application authorized event processed successfully".to_string(),
        })));
    }

    println!("Received application authorized event: {:?}", request_data); // for debugging to see if this works in prod

    // Forward to Killua bot
    match make_request("discord/application_authorized", request_data, 0_u8).await {
        Ok(_response) => Ok(WebhookResponseType::Json(Json(WebhookResponse {
            success: true,
            message: "Application authorized event processed successfully".to_string(),
        }))),
        Err(_e) => Err(Status::InternalServerError),
    }
}

async fn handle_application_deauthorized(
    webhook: DiscordWebhookEvent,
) -> Result<WebhookResponseType, Status> {
    // Parse the event data
    let event = webhook.event.ok_or(Status::BadRequest)?;
    let data = event.data.ok_or(Status::BadRequest)?;
    let event_data: ApplicationDeauthorizedData =
        serde_json::from_value(data).map_err(|_| Status::BadRequest)?;

    let request_data = ApplicationDeauthorizedRequest {
        application_id: webhook.application_id,
        user: event_data.user,
        timestamp: event.timestamp.unwrap_or_default(),
    };

    // Forward to Killua bot
    match make_request("discord/application_deauthorized", request_data, 0_u8).await {
        Ok(_response) => Ok(WebhookResponseType::Json(Json(WebhookResponse {
            success: true,
            message: "Application deauthorized event processed successfully".to_string(),
        }))),
        Err(_e) => Err(Status::InternalServerError),
    }
}

// Health check endpoint for webhook verification
#[get("/webhooks/discord")]
pub fn webhook_health_check() -> Json<WebhookResponse> {
    Json(WebhookResponse {
        success: true,
        message: "Discord webhook endpoint is active".to_string(),
    })
}
