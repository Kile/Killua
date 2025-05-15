from typing import List

class Permission:
    create_instant_invite = 1 << 0
    kick_members = 1 << 1
    ban_members = 1 << 2
    administrator = 1 << 3
    manage_channels = 1 << 4
    manage_guild = 1 << 5
    add_reaction = 1 << 6
    view_audit_log = 1 << 7
    priority_speaker = 1 << 8
    stream = 1 << 9
    read_messages = 1 << 10
    view_channel = 1 << 10
    send_messages = 1 << 11
    send_tts_messages = 1 << 12
    manage_messages = 1 << 13
    embed_links = 1 << 14
    attach_files = 1 << 15
    read_message_history = 1 << 16
    mention_everyone = 1 << 17
    external_emojis = 1 << 18
    use_external_emojis = 1 << 18
    view_guild_insights = 1 << 19
    connect = 1 << 20
    speak = 1 << 21
    mute_members = 1 << 22
    deafen_members = 1 << 23
    move_members = 1 << 24
    use_voice_activation = 1 << 25
    change_nickname = 1 << 26
    manage_nicknames = 1 << 27
    manage_roles = 1 << 28
    manage_permissions = 1 << 28
    manage_webhooks = 1 << 29
    manage_emojis = 1 << 30
    use_application_commands = 1 << 31
    request_to_speak = 1 << 32
    manage_events = 1 << 33
    manage_threads = 1 << 34
    create_public_threads = 1 << 35
    create_private_threads = 1 << 36
    external_stickers = 1 << 37
    use_external_stickers = 1 << 37
    send_messages_in_threads = 1 << 38
    use_embedded_activities = 1 << 39
    moderate_members = 1 << 40

class PermissionOverwrite:
    def __init__(self):
        self.allow: int = 0
        self.deny: int = 0

    def allow_perms(self, perms: List[Permission]) -> None:
        for val in perms:
            self.allow |= int(val)

    def deny_perms(self, perms: List[Permission]) -> None:
        for val in perms:
            self.deny |= int(val)

class Permissions:
    def __init__(self, permissions: int = 0, **kwargs):
        self.value = permissions
        for key, value in kwargs.items():
            setattr(self, key, value)
            
        self.overwrites = []

    def add_overwrite(self, **kwargs):
        overwrite = {}
        
        overwrite["type"] = kwargs.pop("type", 1) # For testing usecase it will be a member most of the time
        # 0 - role
        # 1 - member
        overwrite["id"] = kwargs.pop("id") # I raise an error here because if the id is not provided
        # this enitre method has no point
        if "permissions" in kwargs: # Reads the permission from the enum shortcut
            overwrite["allow"] = kwargs["permissions"].allow
            overwrite["deny"] = kwargs["permissions"].deny
        else:
            overwrite["allow"] = kwargs["allow"]
            overwrite["deny"] = kwargs["deny"]

        self.overwrites.append(overwrite)