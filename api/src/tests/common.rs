use std::{process::Command, sync::Once};
use zmq::{Context, Message, SocketType::ROUTER};

pub static INIT: Once = Once::new();

#[allow(dead_code)]
#[derive(serde::Deserialize)]
struct Request {
    route: String,
    data: serde_json::Value,
}

/// Spins up a zmq server in the background
/// with the provided response.
pub fn test_zmq_server() {
    let context = Context::new();
    let responder = context.socket(ROUTER).unwrap();

    assert!(responder.set_rcvtimeo(5000).is_ok());
    assert!(responder.set_linger(0).is_ok());
    assert!(responder.bind("tcp://127.0.0.1:3210").is_ok());

    // Wait for a request in the background
    std::thread::spawn(move || {
        let poller = responder.as_poll_item(zmq::POLLIN);
        let items = &mut [poller];

        loop {
            if zmq::poll(items, -1).is_err() {
                continue; // Skip to the next iteration if polling fails
            }
            let mut identity = Message::new();
            responder.recv(&mut identity, 0).unwrap();
            let mut buffer = Message::new();
            responder.recv(&mut buffer, 0).unwrap();
            let mut msg = Message::new();
            responder.recv(&mut msg, 0).unwrap();

            let stripped: Vec<u8> = (msg.as_ref() as &[u8])[1..].to_vec();
            let raw_json = String::from_utf8(stripped.clone()).unwrap_or_default();

            let respond_with = match serde_json::from_str::<serde_json::Value>(&raw_json) {
                Ok(request_val) => {
                    let route = request_val["route"].as_str().unwrap_or_default();
                    if route == "update" {
                        let cmd = request_val["data"].as_str().unwrap_or_default();
                        let output = Command::new("sh")
                            .current_dir("..")
                            .arg("-c")
                            .arg(cmd)
                            .output();
                        match output {
                            Ok(output) => {
                                let exit_code = output.status.code().unwrap_or(-1);
                                let stdout = String::from_utf8_lossy(&output.stdout);
                                let stderr = String::from_utf8_lossy(&output.stderr);
                                format!("EXIT_CODE={exit_code}\nOUTPUT={stdout}{stderr}")
                            }
                            Err(e) => format!("EXIT_CODE=-1\nOUTPUT=Failed to run command: {e}"),
                        }
                    } else {
                        match route {
                            "commands" => {
                                r#"{"CATEGORY": {"name": "category", "description": "", "emoji": {"normal": "a", "unicode": "b"}, "commands": []}}"#.to_string()
                            }
                            "stats" => r#"{"guilds": 1, "shards": 1, "registered_users": 1, "user_installs": 1, "last_restart": 1.0}"#.to_string(),
                            "vote" => r#"{"success": "true"}"#.to_string(),
                            "heartbeat" => r#"{"success": "true"}"#.to_string(),
                            "user/info" => {
                                r#"{
                                    "id": "123456789",
                                    "email": "user@example.com",
                                    "display_name": "Test User",
                                    "avatar_url": "https://cdn.discordapp.com/avatars/123456789/avatar.png",
                                    "jenny": 1000,
                                    "daily_cooldown": "2025-01-01T12:00:00",
                                    "met_user": ["111111111", "222222222"],
                                    "effects": {},
                                    "rs_cards": [],
                                    "fs_cards": [],
                                    "badges": ["developer"],
                                    "rps_stats": {"pvp": {"won": 10, "lost": 5, "tied": 2}},
                                    "counting_highscore": {"easy": 3, "hard": 1},
                                    "trivia_stats": {"easy": {"right": 5, "wrong": 2}},
                                    "achievements": ["first_win"],
                                    "votes": 50,
                                    "voting_streak": {"topgg": {"streak": 5}},
                                    "voting_reminder": true,
                                    "premium_guilds": {},
                                    "lootboxes": [1, 2, 3],
                                    "boosters": {"1": 5, "2": 3},
                                    "weekly_cooldown": "2025-01-01T12:00:00",
                                    "action_settings": {"hug": true},
                                    "action_stats": {"hug": {"used": 10}},
                                    "locale": "en-US",
                                    "has_user_installed": true,
                                    "is_premium": true,
                                    "premium_tier": "2",
                                    "email_notifications": {"news": true, "updates": false, "posts": true}
                                }"#.to_string()
                            }
                            "discord/application_authorized" => r#"{"success": true, "message": "Application authorized event processed successfully"}"#.to_string(),
                            "discord/application_deauthorized" => r#"{"success": true, "message": "Application deauthorized event processed successfully"}"#.to_string(),
                            "user_get_basic_details" => r#"{"display_name": "Test User", "avatar_url": "https://cdn.discordapp.com/avatars/123456789/avatar.png"}"#.to_string(),
                            "news/save" => r#"{"news_id": "test_news_id", "message_id": 1234567890123456789}"#.to_string(),
                            "news/delete" => r#"{"status": "deleted"}"#.to_string(),
                            "news/edit" => r#"{"news_id": "test_news_id", "message_id": 1234567890123456789}"#.to_string(),
                            "user/edit" => r#"{"success": true, "message": "User settings updated successfully"}"#.to_string(),
                            "guild/info" => r#"{
                                "badges": ["partner"],
                                "approximate_member_count": 1500,
                                "name": "Test Server",
                                "icon_url": "https://cdn.discordapp.com/icons/111222333444555666/icon.png",
                                "prefix": "!",
                                "is_premium": true,
                                "bot_added_on": "2024-01-15T12:00:00",
                                "tags": [
                                    {
                                        "name": "welcome",
                                        "created_at": "2024-02-01T10:30:00",
                                        "owner": {
                                            "user_id": 123456789,
                                            "display_name": "Test User",
                                            "avatar_url": "https://cdn.discordapp.com/avatars/123456789/avatar.png"
                                        },
                                        "content": "Welcome to the server!",
                                        "uses": 42
                                    }
                                ]
                            }"#.to_string(),
                            "guild/edit" => r#"{"success": true, "message": "Guild settings updated successfully"}"#.to_string(),
                            "guild/editable" => {
                                // Simulating bot returning an empty list [] instead of expected object when no guilds match
                                if raw_json.contains("\"guild_ids\": [0]") || raw_json.contains("\"guild_ids\":[0]") {
                                    "[]".to_string()
                                } else {
                                    r#"{"editable": [111222333444555666], "premium": [111222333444555666]}"#.to_string()
                                }
                            },
                            "guild/tag/create" => r#"{"success": true, "message": "Tag created successfully"}"#.to_string(),
                            "guild/tag/edit" => r#"{"success": true, "message": "Tag updated successfully"}"#.to_string(),
                            "guild/tag/delete" => r#"{"success": true, "message": "Tag deleted successfully"}"#.to_string(),
                            "guild/command_usage" => {
                                if raw_json.contains("\"guild_id\": 0") || raw_json.contains("\"guild_id\":0") {
                                    "".to_string()
                                } else {
                                    r#"[
                                        {
                                            "name": "ping",
                                            "group": "general",
                                            "command_id": 1,
                                            "values": [["1704067200", 10], ["1704070800", 15]]
                                        },
                                        {
                                            "name": "help",
                                            "group": "general",
                                            "command_id": 2,
                                            "values": [["1704067200", 5], ["1704070800", 8]]
                                        }
                                    ]"#.to_string()
                                }
                            },
                            _ => r#"{}"#.to_string(),
                        }
                    }
                }
                Err(_) => r#"{}"#.to_string(),
            };
            let buffer = Message::from("");
            let message = Message::from(respond_with.as_str());
            responder
                .send_multipart(vec![identity, buffer, message], 0)
                .unwrap();
        }
    });
}

/// Gets the API key from Rocket.toml
pub fn get_key() -> String {
    std::env::var("API_KEY").unwrap()
}
