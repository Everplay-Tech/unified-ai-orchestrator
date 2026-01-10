"""Configuration loader"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import toml

# Try to use tomllib (Python 3.11+) for reading, fallback to toml
try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    HAS_TOMLLIB = False


@dataclass
class ToolConfig:
    """Configuration for a specific tool"""
    api_key_env: Optional[str] = None
    enabled: bool = True
    model: Optional[str] = None
    api_key: Optional[str] = None  # Can be set directly (encrypted)


@dataclass
class StorageConfig:
    """Storage configuration"""
    db_type: str = "sqlite"  # "postgresql" or "sqlite"
    db_path: str = "~/.uai/db.sqlite"  # For SQLite
    connection_string: Optional[str] = None  # For PostgreSQL (e.g., "postgresql://user:pass@localhost/dbname")
    index_path: str = "~/.uai/indexes"


@dataclass
class RoutingConfig:
    """Routing configuration"""
    default_tool: str = "claude"
    code_editing: List[str] = field(default_factory=lambda: ["claude"])
    research: List[str] = field(default_factory=lambda: ["claude"])
    general_chat: List[str] = field(default_factory=lambda: ["claude", "gpt"])


@dataclass
class CodebaseConfig:
    """Codebase indexing configuration"""
    auto_index: bool = True
    watch_paths: List[str] = field(default_factory=lambda: ["~/projects"])
    index_depth: int = 3


@dataclass
class APIConfig:
    """API configuration for mobile access"""
    enable_mobile: bool = True
    api_key: Optional[str] = None  # Stored in keyring, not in config file
    allowed_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limit_per_minute: int = 60


@dataclass
class Config:
    """Main configuration"""
    storage: StorageConfig = field(default_factory=StorageConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    codebase: CodebaseConfig = field(default_factory=CodebaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    tools: Dict[str, ToolConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary"""
        config = cls()
        
        if "storage" in data:
            storage_data = data["storage"]
            config.storage = StorageConfig(
                db_type=storage_data.get("db_type", "sqlite"),
                db_path=storage_data.get("db_path", "~/.uai/db.sqlite"),
                connection_string=storage_data.get("connection_string"),
                index_path=storage_data.get("index_path", "~/.uai/indexes"),
            )
        
        if "routing" in data:
            config.routing = RoutingConfig(**data["routing"])
        
        if "codebase" in data:
            config.codebase = CodebaseConfig(**data["codebase"])
        
        if "api" in data:
            config.api = APIConfig(**data["api"])
        
        if "tools" in data:
            for tool_name, tool_data in data["tools"].items():
                config.tools[tool_name] = ToolConfig(**tool_data)
        
        return config

    def to_dict(self) -> dict:
        """Convert Config to dictionary"""
        result = {
            "storage": {
                "db_type": self.storage.db_type,
                "db_path": self.storage.db_path,
                "connection_string": self.storage.connection_string,
                "index_path": self.storage.index_path,
            },
            "routing": {
                "default_tool": self.routing.default_tool,
                "code_editing": self.routing.code_editing,
                "research": self.routing.research,
                "general_chat": self.routing.general_chat,
            },
            "codebase": {
                "auto_index": self.codebase.auto_index,
                "watch_paths": self.codebase.watch_paths,
                "index_depth": self.codebase.index_depth,
            },
            "api": {
                "enable_mobile": self.api.enable_mobile,
                "allowed_origins": self.api.allowed_origins,
                "rate_limit_per_minute": self.api.rate_limit_per_minute,
            },
            "tools": {},
        }
        
        for tool_name, tool_config in self.tools.items():
            result["tools"][tool_name] = {
                "api_key_env": tool_config.api_key_env,
                "enabled": tool_config.enabled,
                "model": tool_config.model,
            }
        
        return result


def get_config_path() -> Path:
    """Get path to config file"""
    config_dir = Path.home() / ".uai"
    return config_dir / "config.toml"


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file"""
    if config_path is None:
        config_path = get_config_path()
    
    # Expand user directory
    config_path = Path(config_path).expanduser()
    
    # Create default config if file doesn't exist
    if not config_path.exists():
        config = Config()
        save_config(config, config_path)
        return config
    
    # Load from file
    if HAS_TOMLLIB:
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
    else:
        with open(config_path, "r") as f:
            data = toml.load(f)
    
    config = Config.from_dict(data)
    
    # Load API keys from environment variables
    for tool_name, tool_config in config.tools.items():
        if tool_config.api_key_env:
            api_key = os.getenv(tool_config.api_key_env)
            if api_key:
                tool_config.api_key = api_key
    
    # Load mobile API key from keyring if not in config
    if not config.api.api_key:
        try:
            from ..utils.auth import get_secret
            mobile_api_key = get_secret("mobile_api_key")
            if mobile_api_key:
                config.api.api_key = mobile_api_key
        except Exception:
            pass
    
    return config


def save_config(config: Config, config_path: Optional[Path] = None) -> None:
    """Save configuration to file"""
    if config_path is None:
        config_path = get_config_path()
    
    config_path = Path(config_path).expanduser()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    data = config.to_dict()
    
    with open(config_path, "w") as f:
        toml.dump(data, f)
