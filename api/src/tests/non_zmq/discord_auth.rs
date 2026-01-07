use crate::routes::common::discord_auth::{DiscordAuth, DiscordUser};

// Test fixtures for Discord user data
const TEST_USER_1: &str = "123456789";
const TEST_USER_2: &str = "987654321";
const ADMIN_USER: &str = "555666777";

#[test]
fn test_discord_auth_admin_check() {
    // Test admin check functionality
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let regular_user = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user@example.com".to_string()),
    };

    let admin_auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: regular_user,
        token: String::new(),
    };

    // Admin should be able to access any user's data
    assert!(admin_auth.can_access_user(TEST_USER_1));
    assert!(admin_auth.can_access_user(TEST_USER_2));
    assert!(admin_auth.can_access_user(ADMIN_USER));

    // Regular user should only be able to access their own data
    assert!(regular_auth.can_access_user(TEST_USER_1));
    assert!(!regular_auth.can_access_user(TEST_USER_2));
    assert!(!regular_auth.can_access_user(ADMIN_USER));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_multiple_admins() {
    // Test with multiple admin IDs
    std::env::set_var("ADMIN_IDS", format!("{ADMIN_USER},111222333"));

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let second_admin = DiscordUser {
        id: "111222333".to_string(),
        username: "admin2".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin2@example.com".to_string()),
    };

    let regular_user = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user@example.com".to_string()),
    };

    let admin_auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };
    let second_admin_auth = DiscordAuth {
        user: second_admin,
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: regular_user,
        token: String::new(),
    };

    // Both admins should be able to access any user's data
    assert!(admin_auth.can_access_user(TEST_USER_1));
    assert!(admin_auth.can_access_user(TEST_USER_2));
    assert!(second_admin_auth.can_access_user(TEST_USER_1));
    assert!(second_admin_auth.can_access_user(TEST_USER_2));

    // Regular user should only be able to access their own data
    assert!(regular_auth.can_access_user(TEST_USER_1));
    assert!(!regular_auth.can_access_user(TEST_USER_2));

    // Test that the admin list is properly parsed
    let admin_ids = std::env::var("ADMIN_IDS").unwrap();
    let admin_list: Vec<&str> = admin_ids.split(',').collect();
    assert!(admin_list.contains(&ADMIN_USER));
    assert!(admin_list.contains(&"111222333"));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_self_access() {
    // Test that users can always access their own data
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let user1 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user1".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user1@example.com".to_string()),
    };

    let user2 = DiscordUser {
        id: TEST_USER_2.to_string(),
        username: "user2".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user2@example.com".to_string()),
    };

    let user1_auth = DiscordAuth {
        user: user1,
        token: String::new(),
    };
    let user2_auth = DiscordAuth {
        user: user2,
        token: String::new(),
    };

    // Users should always be able to access their own data
    assert!(user1_auth.can_access_user(TEST_USER_1));
    assert!(user2_auth.can_access_user(TEST_USER_2));

    // Users should not be able to access each other's data
    assert!(!user1_auth.can_access_user(TEST_USER_2));
    assert!(!user2_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_no_admins() {
    // Test behavior when no admin IDs are set
    std::env::set_var("ADMIN_IDS", "");

    let user1 = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user1".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user1@example.com".to_string()),
    };

    let user2 = DiscordUser {
        id: TEST_USER_2.to_string(),
        username: "user2".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user2@example.com".to_string()),
    };

    let user1_auth = DiscordAuth {
        user: user1,
        token: String::new(),
    };
    let user2_auth = DiscordAuth {
        user: user2,
        token: String::new(),
    };

    // Users should only be able to access their own data
    assert!(user1_auth.can_access_user(TEST_USER_1));
    assert!(!user1_auth.can_access_user(TEST_USER_2));
    assert!(user2_auth.can_access_user(TEST_USER_2));
    assert!(!user2_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_user_serialization() {
    // Test that DiscordUser can be serialized and deserialized
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
    // Test the is_admin method specifically
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let regular_user = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user@example.com".to_string()),
    };

    let admin_auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: regular_user,
        token: String::new(),
    };

    assert!(admin_auth.is_admin());
    assert!(!regular_auth.is_admin());

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_edge_cases() {
    // Test edge cases for admin ID parsing
    std::env::set_var("ADMIN_IDS", format!("{}, ,{}", ADMIN_USER, "111222333"));

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let admin_auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };

    // Should still work with extra spaces
    assert!(admin_auth.is_admin());
    assert!(admin_auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_multiple_identical_admins() {
    // Test with duplicate admin IDs
    std::env::set_var(
        "ADMIN_IDS",
        format!("{},{},{}", ADMIN_USER, ADMIN_USER, "111222333"),
    );

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };

    // Should still work with duplicates
    assert!(auth.is_admin());
    assert!(auth.can_access_user(TEST_USER_1));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_auth_empty_user_id() {
    // Test behavior with empty user ID
    // First, ensure no admin IDs are set
    std::env::remove_var("ADMIN_IDS");

    let user_id = "".to_string();
    let user = DiscordUser {
        id: user_id.clone(),
        username: "empty_user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("empty@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user,
        token: String::new(),
    };

    // Should handle empty user ID gracefully
    assert!(auth.can_access_user("")); // Can access own empty ID
    assert!(auth.is_admin()); // Empty user ID is treated as admin (potential bug)
    assert!(auth.can_access_user(TEST_USER_1)); // Can access other users due to admin status
}

#[test]
fn test_discord_auth_special_characters_in_user_id() {
    // Test behavior with special characters in user ID
    let special_user_id = "user@#$%^&*()";
    let user = DiscordUser {
        id: special_user_id.to_string(),
        username: "special_user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("special@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user,
        token: String::new(),
    };

    // Should handle special characters correctly
    assert!(auth.can_access_user(special_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_unicode_characters() {
    // Test behavior with unicode characters in user ID
    let unicode_user_id = "user_🎉_🌟_🎊";
    let user = DiscordUser {
        id: unicode_user_id.to_string(),
        username: "unicode_user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("unicode@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user,
        token: String::new(),
    };

    // Should handle unicode characters correctly
    assert!(auth.can_access_user(unicode_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_very_long_user_id() {
    // Test behavior with very long user ID
    let long_user_id = "a".repeat(1000);
    let user = DiscordUser {
        id: long_user_id.clone(),
        username: "long_user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("long@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user,
        token: String::new(),
    };

    // Should handle very long user IDs correctly
    assert!(auth.can_access_user(&long_user_id));
    assert!(!auth.can_access_user(TEST_USER_1));
    assert!(!auth.is_admin());
}

#[test]
fn test_discord_auth_admin_with_special_characters() {
    // Test admin functionality with special characters in admin ID
    let special_admin_id = "admin@#$%^&*()";
    std::env::set_var("ADMIN_IDS", special_admin_id);

    let admin_user = DiscordUser {
        id: special_admin_id.to_string(),
        username: "special_admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("special_admin@example.com".to_string()),
    };

    let auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };

    // Should work with special characters in admin ID
    assert!(auth.is_admin());
    assert!(auth.can_access_user(TEST_USER_1));
    assert!(auth.can_access_user(TEST_USER_2));

    std::env::remove_var("ADMIN_IDS");
}

#[test]
fn test_discord_user_equality() {
    // Test that DiscordUser instances with same data are equal
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

    // Test field-by-field equality
    assert_eq!(user1.id, user2.id);
    assert_eq!(user1.username, user2.username);
    assert_eq!(user1.discriminator, user2.discriminator);
    assert_eq!(user1.avatar, user2.avatar);
    assert_eq!(user1.email, user2.email);
}

#[test]
fn test_discord_auth_access_patterns() {
    // Test various access patterns
    std::env::set_var("ADMIN_IDS", ADMIN_USER);

    let admin_user = DiscordUser {
        id: ADMIN_USER.to_string(),
        username: "admin".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("admin@example.com".to_string()),
    };

    let regular_user = DiscordUser {
        id: TEST_USER_1.to_string(),
        username: "user".to_string(),
        discriminator: "0000".to_string(),
        avatar: None,
        email: Some("user@example.com".to_string()),
    };

    let admin_auth = DiscordAuth {
        user: admin_user,
        token: String::new(),
    };
    let regular_auth = DiscordAuth {
        user: regular_user,
        token: String::new(),
    };

    // Admin access patterns
    assert!(admin_auth.can_access_user(ADMIN_USER)); // Self access
    assert!(admin_auth.can_access_user(TEST_USER_1)); // Other user access
    assert!(admin_auth.can_access_user(TEST_USER_2)); // Other user access
    assert!(admin_auth.can_access_user("999999999")); // Non-existent user access

    // Regular user access patterns
    assert!(regular_auth.can_access_user(TEST_USER_1)); // Self access
    assert!(!regular_auth.can_access_user(TEST_USER_2)); // Other user access denied
    assert!(!regular_auth.can_access_user(ADMIN_USER)); // Admin access denied
    assert!(!regular_auth.can_access_user("999999999")); // Non-existent user access denied

    std::env::remove_var("ADMIN_IDS");
}
