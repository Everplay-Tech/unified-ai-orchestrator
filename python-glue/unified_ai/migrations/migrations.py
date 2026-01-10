"""Migration definitions for both PostgreSQL and SQLite"""

# Migration 1: Initial schema
MIGRATION_001_UP_SQLITE = """
CREATE TABLE IF NOT EXISTS contexts (
    conversation_id TEXT PRIMARY KEY,
    project_id TEXT,
    data TEXT NOT NULL,
    updated_at INTEGER NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON contexts(updated_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
"""

MIGRATION_001_DOWN_SQLITE = """
DROP INDEX IF EXISTS idx_messages_timestamp;
DROP INDEX IF EXISTS idx_messages_conversation_id;
DROP INDEX IF EXISTS idx_contexts_updated_at;
DROP INDEX IF EXISTS idx_contexts_project_id;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS contexts;
"""

MIGRATION_001_UP_POSTGRESQL = """
CREATE TABLE IF NOT EXISTS contexts (
    conversation_id VARCHAR(255) PRIMARY KEY,
    project_id VARCHAR(255),
    data TEXT NOT NULL,
    updated_at BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    timestamp BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES contexts(conversation_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_contexts_project_id ON contexts(project_id);
CREATE INDEX IF NOT EXISTS idx_contexts_updated_at ON contexts(updated_at);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
"""

MIGRATION_001_DOWN_POSTGRESQL = """
DROP INDEX IF EXISTS idx_messages_timestamp;
DROP INDEX IF EXISTS idx_messages_conversation_id;
DROP INDEX IF EXISTS idx_contexts_updated_at;
DROP INDEX IF EXISTS idx_contexts_project_id;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS contexts;
"""

# Migration 2: Cost tracking
MIGRATION_002_UP_SQLITE = """
CREATE TABLE IF NOT EXISTS cost_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    conversation_id TEXT,
    project_id TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_cost_records_tool ON cost_records(tool);
CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id);
CREATE INDEX IF NOT EXISTS idx_cost_records_created_at ON cost_records(created_at);
"""

MIGRATION_002_DOWN_SQLITE = """
DROP INDEX IF EXISTS idx_cost_records_created_at;
DROP INDEX IF EXISTS idx_cost_records_project_id;
DROP INDEX IF EXISTS idx_cost_records_tool;
DROP TABLE IF EXISTS cost_records;
"""

MIGRATION_002_UP_POSTGRESQL = """
CREATE TABLE IF NOT EXISTS cost_records (
    id SERIAL PRIMARY KEY,
    tool VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    conversation_id VARCHAR(255),
    project_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cost_records_tool ON cost_records(tool);
CREATE INDEX IF NOT EXISTS idx_cost_records_project_id ON cost_records(project_id);
CREATE INDEX IF NOT EXISTS idx_cost_records_created_at ON cost_records(created_at);
"""

MIGRATION_002_DOWN_POSTGRESQL = """
DROP INDEX IF EXISTS idx_cost_records_created_at;
DROP INDEX IF EXISTS idx_cost_records_project_id;
DROP INDEX IF EXISTS idx_cost_records_tool;
DROP TABLE IF EXISTS cost_records;
"""

# Migration 3: Indexing (placeholder - will be implemented later)
MIGRATION_003_UP_SQLITE = """
-- Indexing tables will be created by the indexer module
-- This migration is a placeholder
"""

MIGRATION_003_DOWN_SQLITE = """
-- No-op
"""

MIGRATION_003_UP_POSTGRESQL = """
-- Indexing tables will be created by the indexer module
-- This migration is a placeholder
"""

MIGRATION_003_DOWN_POSTGRESQL = """
-- No-op
"""

# Migration 4: Security (users, API keys, audit logs)
MIGRATION_004_UP_SQLITE = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    role TEXT NOT NULL DEFAULT 'user',
    api_key_hash TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE TABLE IF NOT EXISTS api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    name TEXT,
    expires_at INTEGER,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    revoked_at INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    user_id TEXT,
    resource_type TEXT,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    details TEXT,
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
"""

MIGRATION_004_DOWN_SQLITE = """
DROP INDEX IF EXISTS idx_audit_logs_created_at;
DROP INDEX IF EXISTS idx_audit_logs_event_type;
DROP INDEX IF EXISTS idx_audit_logs_user_id;
DROP INDEX IF EXISTS idx_api_keys_key_hash;
DROP INDEX IF EXISTS idx_api_keys_user_id;
DROP INDEX IF EXISTS idx_users_api_key_hash;
DROP INDEX IF EXISTS idx_users_username;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;
"""

MIGRATION_004_UP_POSTGRESQL = """
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE,
    password_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    api_key_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(255) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255),
    expires_at BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    user_id VARCHAR(255),
    resource_type VARCHAR(100),
    resource_id VARCHAR(255),
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_api_key_hash ON users(api_key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
"""

MIGRATION_004_DOWN_POSTGRESQL = """
DROP INDEX IF EXISTS idx_audit_logs_created_at;
DROP INDEX IF EXISTS idx_audit_logs_event_type;
DROP INDEX IF EXISTS idx_audit_logs_user_id;
DROP INDEX IF EXISTS idx_api_keys_key_hash;
DROP INDEX IF EXISTS idx_api_keys_user_id;
DROP INDEX IF EXISTS idx_users_api_key_hash;
DROP INDEX IF EXISTS idx_users_username;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS users;
"""

# Migration registry
MIGRATIONS = [
    {
        "version": 1,
        "name": "initial_schema",
        "up_sqlite": MIGRATION_001_UP_SQLITE,
        "down_sqlite": MIGRATION_001_DOWN_SQLITE,
        "up_postgresql": MIGRATION_001_UP_POSTGRESQL,
        "down_postgresql": MIGRATION_001_DOWN_POSTGRESQL,
    },
    {
        "version": 2,
        "name": "add_cost_tracking",
        "up_sqlite": MIGRATION_002_UP_SQLITE,
        "down_sqlite": MIGRATION_002_DOWN_SQLITE,
        "up_postgresql": MIGRATION_002_UP_POSTGRESQL,
        "down_postgresql": MIGRATION_002_DOWN_POSTGRESQL,
    },
    {
        "version": 3,
        "name": "add_indexing",
        "up_sqlite": MIGRATION_003_UP_SQLITE,
        "down_sqlite": MIGRATION_003_DOWN_SQLITE,
        "up_postgresql": MIGRATION_003_UP_POSTGRESQL,
        "down_postgresql": MIGRATION_003_DOWN_POSTGRESQL,
    },
    {
        "version": 4,
        "name": "add_security",
        "up_sqlite": MIGRATION_004_UP_SQLITE,
        "down_sqlite": MIGRATION_004_DOWN_SQLITE,
        "up_postgresql": MIGRATION_004_UP_POSTGRESQL,
        "down_postgresql": MIGRATION_004_DOWN_POSTGRESQL,
    },
]
