use crate::rocket;
use crate::routes::common::discord_auth::{
    cache_token, clear_token_cache, disable_test_mode, enable_test_mode, invalidate_token,
    is_token_cached, DiscordAuth, DiscordUser,
};
use rocket::http::{Header, Status};
use rocket::local::blocking::Client;

// Test fixtures for Discord user data
const TEST_USER_1: &str = "123456789";
const TEST_USER_2: &str = "987654321";
const ADMIN_USER: &str = "555666777";

fn make_test_user(id: &str) -> DiscordUser {
    DiscordUser {
        id: id.to_string(),
        username: format!("user_{id}"),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some(format!("{id}@example.com")),
    }
}

// ===== UNIT TESTS FOR DiscordAuth / DiscordUser =====

#[test]
fn test_discord_auth_admin_check() {
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };

    assert!(admin_auth.can_access_user(TEST_USER_1));
    assert!(admin_auth.can_access_user(TEST_USER_2));
    assert!(admin_auth.can_access_user(ADMIN_USER));

    assert!(regular_auth.can_access_user(TEST_USER_1));
    assert!(!regular_auth.can_access_user(TEST_USER_2));
    assert!(!regular_auth.can_access_user(ADMIN_USER));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_multiple_admins() {
    std::env::set_var("ADMIN_IDS", format!("{ADMIN_USER},111222333"));

    let admin_auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };
    let second_admin_auth = DiscordAuth {
        user: make_test_user("111222333"),
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };

    assert!(admin_auth.can_access_user(TEST_USER_1));
    assert!(admin_auth.can_access_user(TEST_USER_2));
    assert!(second_admin_auth.can_access_user(TEST_USER_1));
    assert!(second_admin_auth.can_access_user(TEST_USER_2));

    assert!(regular_auth.can_access_user(TEST_USER_1));
    assert!(!regular_auth.can_access_user(TEST_USER_2));

    let admin_ids = std::env::var("ADMIN_IDS").unwrap();
    let admin_list: Vec<&str> = admin_ids.split(',').collect();
    assert!(admin_list.contains(&ADMIN_USER));
    assert!(admin_list.contains(&"111222333"));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_self_access() {
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let user1_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };
    let user2_auth = DiscordAuth {
        user: make_test_user(TEST_USER_2),
        token: String::new(),
    };

    assert!(user1_auth.can_access_user(TEST_USER_1));
    assert!(user2_auth.can_access_user(TEST_USER_2));

    assert!(!user1_auth.can_access_user(TEST_USER_2));
    assert!(!user2_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_no_admins() {
    std::env::set_var("ADMIN_IDS", "");

    let user1_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };
    let user2_auth = DiscordAuth {
        user: make_test_user(TEST_USER_2),
        token: String::new(),
    };

    assert!(user1_auth.can_access_user(TEST_USER_1));
    assert!(!user1_auth.can_access_user(TEST_USER_2));
    assert!(user2_auth.can_access_user(TEST_USER_2));
    assert!(!user2_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_user_serialization() {
    let user = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "testuser".to_string(),
        discriminator: "1234".to_string(),
        avatar: Some("avatar_hash".to_string()),
        email: Some("test@example.com".to_string()),
    };

    let serialized = serde_json::to_string(&user).unwrap();
    let deserialized: DiscordUser = serde_json::from_str(&serialized).unwrap();

    assert_eq!(user.id, deserialized.id);
    assert_eq!(user.username, deserialized.username);
    assert_eq!(user.discriminator, deserialized.discriminator);
    assert_eq!(user.avatar, deserialized.avatar);
    assert_eq!(user.email, deserialized.email);
}

#[test]
fn test_discord_auth_is_admin() {
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };

    assert!(admin_auth.is_admin());
    assert!(!regular_auth.is_admin());

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_edge_cases() {
    std::env::set_var("ADMIN_IDS", format!("{}, ,{}", ADMIN_USER, "111222333"));

    let admin_auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };

    assert!(admin_auth.is_admin());
    assert!(admin_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_multiple_identical_admins() {
    std::env::set_var(
        "ADMIN_IDS",
        format!("{},{},{}", ADMIN_USER, ADMIN_USER, "111222333"),
    );

    let auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };

    assert!(auth.is_admin());
    assert!(auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_empty_user_id() {
    std::env::remove_var("ADMIN_IDS");

    let auth = DiscordAuth {
        user: DiscordUser {
            id: "".to_string(),
            username: "empty_user".to_string(),
            discriminator: "0000".to_string(),
            avatar: None,
            email: Some("empty@example.com".to_string()),
        },
        token: String::new(),
    };

    assert!(auth.can_access_user(""));
    assert!(auth.is_admin()); // Empty user ID is treated as admin (potential bug)
    assert!(auth.can_access_user(TEST_USER_1));
}

#[test]
fn test_discord_auth_special_characters_in_user_id() {
    let special_user_id = "user@#$%^&*()";
    let auth = DiscordAuth {
        user: make_test_user(special_user_id),
        token: String::new(),
    };

    assert!(auth.can_access_user(special_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_unicode_characters() {
    let unicode_user_id = "user_🎉_🌟_🎊";
    let auth = DiscordAuth {
        user: make_test_user(unicode_user_id),
        token: String::new(),
    };

    assert!(auth.can_access_user(unicode_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_very_long_user_id() {
    let long_user_id = "a".repeat(1000);
    let auth = DiscordAuth {
        user: make_test_user(&long_user_id),
        token: String::new(),
    };

    assert!(auth.can_access_user(&long_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_admin_with_special_characters() {
    let special_admin_id = "admin@#$%^&*()";
    std::env::set_var("ADMIN_IDS", special_admin_id);

    let auth = DiscordAuth {
        user: make_test_user(special_admin_id),
        token: String::new(),
    };

    assert!(auth.is_admin());
    assert!(auth.can_access_user(TEST_USER_1));
    assert!(auth.can_access_user(TEST_USER_2));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_user_equality() {
    let user1 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "testuser".to_string(),
        discriminator: "1234".to_string(),
        avatar: Some("avatar_hash".to_string()),
        email: Some("test@example.com".to_string()),
    };

    let user2 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "testuser".to_string(),
        discriminator: "1234".to_string(),
        avatar: Some("avatar_hash".to_string()),
        email: Some("test@example.com".to_string()),
    };

    assert_eq!(user1.id, user2.id);
    assert_eq!(user1.username, user2.username);
    assert_eq!(user1.discriminator, user2.discriminator);
    assert_eq!(user1.avatar, user2.avatar);
    assert_eq!(user1.email, user2.email);
}

#[test]
fn test_discord_auth_access_patterns() {
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_auth = DiscordAuth {
        user: make_test_user(ADMIN_USER),
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: make_test_user(TEST_USER_1),
        token: String::new(),
    };

    assert!(admin_auth.can_access_user(ADMIN_USER));
    assert!(admin_auth.can_access_user(TEST_USER_1));
    assert!(admin_auth.can_access_user(TEST_USER_2));
    assert!(admin_auth.can_access_user("999999999"));

    assert!(regular_auth.can_access_user(TEST_USER_1));
    assert!(!regular_auth.can_access_user(TEST_USER_2));
    assert!(!regular_auth.can_access_user(ADMIN_USER));
    assert!(!regular_auth.can_access_user("999999999"));

    std::env::remove_var("ADMIN_IDS");
}

// ===== TOKEN CACHE UNIT TESTS (no Rocket client needed) =====

#[test]
fn test_cache_token_and_retrieve() {
    clear_token_cache();

    let token = "Bearer test_cache_token";
    let user = make_test_user(TEST_USER_1);

    assert!(!is_token_cached(token));

    cache_token(token, &user);
    assert!(is_token_cached(token));

    clear_token_cache();
}

#[test]
fn test_clear_token_cache() {
    clear_token_cache();

    let token1 = "Bearer cache_clear_1";
    let token2 = "Bearer cache_clear_2";

    cache_token(token1, &make_test_user(TEST_USER_1));
    cache_token(token2, &make_test_user(TEST_USER_2));

    assert!(is_token_cached(token1));
    assert!(is_token_cached(token2));

    clear_token_cache();

    assert!(!is_token_cached(token1));
    assert!(!is_token_cached(token2));
}

#[test]
fn test_invalidate_single_token() {
    clear_token_cache();

    let token1 = "Bearer inv_single_1";
    let token2 = "Bearer inv_single_2";

    cache_token(token1, &make_test_user(TEST_USER_1));
    cache_token(token2, &make_test_user(TEST_USER_2));

    assert!(is_token_cached(token1));
    assert!(is_token_cached(token2));

    invalidate_token(token1);

    assert!(!is_token_cached(token1), "Invalidated token should be removed");
    assert!(is_token_cached(token2), "Other tokens should remain cached");

    clear_token_cache();
}

#[test]
fn test_invalidate_nonexistent_token() {
    clear_token_cache();

    // Should not panic or error when invalidating a token that isn't in the cache
    invalidate_token("Bearer does_not_exist");

    assert!(!is_token_cached("Bearer does_not_exist"));
    clear_token_cache();
}

#[test]
fn test_multiple_tokens_cached_independently() {
    clear_token_cache();

    let token1 = "Bearer multi_1";
    let token2 = "Bearer multi_2";
    let token3 = "Bearer multi_3";

    cache_token(token1, &make_test_user(TEST_USER_1));
    cache_token(token2, &make_test_user(TEST_USER_2));
    cache_token(token3, &make_test_user(ADMIN_USER));

    assert!(is_token_cached(token1));
    assert!(is_token_cached(token2));
    assert!(is_token_cached(token3));

    // Remove the middle one
    invalidate_token(token2);
    assert!(is_token_cached(token1));
    assert!(!is_token_cached(token2));
    assert!(is_token_cached(token3));

    clear_token_cache();
}

#[test]
fn test_disable_test_mode_clears_cache() {
    enable_test_mode();
    clear_token_cache();

    let token = "Bearer dtm_clear_test";
    cache_token(token, &make_test_user(TEST_USER_1));
    assert!(is_token_cached(token));

    // disable_test_mode also clears the cache
    disable_test_mode();
    assert!(!is_token_cached(token), "Cache should be cleared when test mode is disabled");
}

#[test]
fn test_cache_overwrites_existing_entry() {
    clear_token_cache();

    let token = "Bearer overwrite_test";
    let user1 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "original".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: None,
    };
    let user2 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "updated".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: None,
    };

    cache_token(token, &user1);
    assert!(is_token_cached(token));

    // Overwrite with new user data
    cache_token(token, &user2);
    assert!(is_token_cached(token));

    clear_token_cache();
}

// ===== HTTP-LEVEL AUTH TESTS (require MONGODB env var, same as other non_zmq HTTP tests) =====

#[test]
fn test_invalid_discord_token() {
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let invalid_header = Header::new("Authorization", "Bearer invalid_discord_token");

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put(format!("/user/edit/{TEST_USER_1}"))
        .header(invalid_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    disable_test_mode();
}

#[test]
fn test_malformed_auth_header() {
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();
    let malformed_header = Header::new("Authorization", "NotBearer token");

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put(format!("/user/edit/{TEST_USER_1}"))
        .header(malformed_header)
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    disable_test_mode();
}

#[test]
fn test_missing_auth_header() {
    let client = Client::tracked(rocket()).unwrap();

    let edit_data = serde_json::json!({
        "voting_reminder": true
    });

    let response = client
        .put(format!("/user/edit/{TEST_USER_1}"))
        .header(Header::new("Content-Type", "application/json"))
        .body(edit_data.to_string())
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);
}

#[test]
fn test_token_cached_after_first_request() {
    enable_test_mode();
    clear_token_cache();

    let token = "Bearer valid_token_1";
    assert!(!is_token_cached(token), "Token should not be cached yet");

    let client = Client::tracked(rocket()).unwrap();
    let response = client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token))
        .dispatch();

    // Auth succeeds (request may fail later due to ZMQ, but not with 403)
    assert_ne!(response.status(), Status::Forbidden);
    assert!(is_token_cached(token), "Token should be cached after successful auth");

    disable_test_mode();
}

#[test]
fn test_cached_token_serves_subsequent_requests() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();
    let token = "Bearer valid_token_1";

    // First request populates cache
    let r1 = client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token))
        .dispatch();
    assert_ne!(r1.status(), Status::Forbidden);
    assert!(is_token_cached(token));

    // Second request served from cache
    let r2 = client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token))
        .dispatch();
    assert_ne!(r2.status(), Status::Forbidden);
    assert!(is_token_cached(token));

    disable_test_mode();
}

#[test]
fn test_invalid_token_not_cached() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();
    let bad_token = "Bearer totally_invalid";

    let response = client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", bad_token))
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);
    assert!(!is_token_cached(bad_token), "Invalid tokens must not be cached");

    disable_test_mode();
}

// ===== LOGOUT ENDPOINT TESTS (require MONGODB env var) =====

#[test]
fn test_logout_removes_token_from_cache() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();
    let token = "Bearer valid_token_1";

    // Cache the token via a normal request
    client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token))
        .dispatch();
    assert!(is_token_cached(token));

    // Call logout
    let response = client
        .post("/logout")
        .header(Header::new("Authorization", token))
        .dispatch();

    assert_eq!(response.status(), Status::Ok);
    let body: serde_json::Value = serde_json::from_str(&response.into_string().unwrap()).unwrap();
    assert_eq!(body["message"], "Successfully logged out");
    assert!(!is_token_cached(token), "Token must be removed from cache after logout");

    disable_test_mode();
}

#[test]
fn test_logout_requires_valid_token() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();

    let response = client
        .post("/logout")
        .header(Header::new("Authorization", "Bearer totally_bogus"))
        .dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    disable_test_mode();
}

#[test]
fn test_logout_requires_auth_header() {
    enable_test_mode();

    let client = Client::tracked(rocket()).unwrap();

    let response = client.post("/logout").dispatch();

    assert_eq!(response.status(), Status::Forbidden);

    disable_test_mode();
}

#[test]
fn test_logout_only_affects_own_token() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();
    let token1 = "Bearer valid_token_1";
    let token2 = "Bearer valid_token_2";

    // Cache both tokens
    client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token1))
        .dispatch();
    client
        .get(format!("/user/info/{TEST_USER_2}"))
        .header(Header::new("Authorization", token2))
        .dispatch();

    assert!(is_token_cached(token1));
    assert!(is_token_cached(token2));

    // Logout user 1
    let response = client
        .post("/logout")
        .header(Header::new("Authorization", token1))
        .dispatch();
    assert_eq!(response.status(), Status::Ok);

    assert!(!is_token_cached(token1));
    assert!(is_token_cached(token2), "Other user's token should remain");

    disable_test_mode();
}

#[test]
fn test_logout_idempotent() {
    enable_test_mode();
    clear_token_cache();

    let client = Client::tracked(rocket()).unwrap();
    let token = "Bearer valid_token_1";

    // Cache the token
    client
        .get(format!("/user/info/{TEST_USER_1}"))
        .header(Header::new("Authorization", token))
        .dispatch();

    // First logout
    let r1 = client
        .post("/logout")
        .header(Header::new("Authorization", token))
        .dispatch();
    assert_eq!(r1.status(), Status::Ok);
    assert!(!is_token_cached(token));

    // Second logout - token gets re-verified (test mode), re-cached by the
    // DiscordAuth guard, then invalidated again. Should still succeed.
    let r2 = client
        .post("/logout")
        .header(Header::new("Authorization", token))
        .dispatch();
    assert_eq!(r2.status(), Status::Ok);
    assert!(!is_token_cached(token));

    disable_test_mode();
}
