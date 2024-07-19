from prometheus_client import Counter, Gauge

METRIC_PREFIX = "discord_"

CONNECTION_GAUGE = Gauge(
    METRIC_PREFIX + "connected",
    "Determines if the bot is connected to Discord",
    ["shard"],
)
LATENCY_GAUGE = Gauge(
    METRIC_PREFIX + "latency",
    "latency to Discord",
    ["shard"],
)
ON_INTERACTION_COUNTER = Counter(
    METRIC_PREFIX + "event_on_interaction",
    "Amount of interactions called by users",
    ["is_user_installed"],
)
ON_COMMAND_COUNTER = Counter(
    METRIC_PREFIX + "event_on_command",
    "Amount of commands called by users",
)
GUILD_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_guilds", "Amount of guild this bot is a member of"
)
CHANNEL_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_channels",
    "Amount of channels this bot is has access to",
)
REGISTERED_USER_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_registered_users",
    "Amount of users registered in the bot",
)

COMMANDS_GAUGE = Gauge(
    METRIC_PREFIX + "stat_total_commands", "Amount of commands registered in the bot"
)

RAM_USAGE_GAUGE = Gauge(METRIC_PREFIX + "ram_usage", "Amount of RAM used by the bot")

CPU_USAGE_GAUGE = Gauge(METRIC_PREFIX + "cpu_usage", "Amount of CPU used by the bot")

MEMORY_USAGE_GAUGE = Gauge(
    METRIC_PREFIX + "memory_usage", "Amount of memory used by the bot"
)

API_REQUESTS_COUNTER = Counter(
    METRIC_PREFIX + "api_requests",
    "Amount of requests made to the Killua API",
    ["endpoint", "type"],
)

API_RESPONSE_TIME = Gauge(
    METRIC_PREFIX + "api_response_time", "Response time of the Killua API"
)

IPC_RESPONSE_TIME = Gauge(
    METRIC_PREFIX + "ipc_response_time", "Response time of the IPC server"
)

API_SPAM_REQUESTS = Counter(
    METRIC_PREFIX + "api_spam_requests",
    "Amount of requests that are attempted malice to my API",
)

DAILY_ACTIVE_USERS = Gauge(
    METRIC_PREFIX + "daily_active_users", "Amount of users that use the bot daily"
)

COMMAND_USAGE = Gauge(
    METRIC_PREFIX + "command_usage",
    "Amount of times a command was used",
    ["group", "command", "command_id"],
)

PREMIUM_USERS = Gauge(
    METRIC_PREFIX + "premium_users", "Amount of users that have premium"
)


VOTES = Counter(
    METRIC_PREFIX + "votes",
    "Amount of votes the bot has received",
    ["platform"],
)

TODO_LISTS = Gauge(METRIC_PREFIX + "todo_lists", "Amount of todo lists created")

TODOS = Gauge(
    METRIC_PREFIX + "todos",
    "Amount of todos created",
)

TAGS = Gauge(
    METRIC_PREFIX + "tags",
    "Amount of tags created",
)

LOCALE = Gauge(
    METRIC_PREFIX + "locale",
    "Where users are from",
    ["country"],
)
