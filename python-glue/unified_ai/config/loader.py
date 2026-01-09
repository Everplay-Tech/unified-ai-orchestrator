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
    db_path: str = "~/.uai/db.sqlite"
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
class Config:
    """Main configuration"""
    storage: StorageConfig = field(default_factory=StorageConfig)
    routing: RoutingConfig = field(default_factory=RoutingConfig)
    codebase: CodebaseConfig = field(default_factory=CodebaseConfig)
    tools: Dict[str, ToolConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary"""
        config = cls()
        
        if "storage" in data:
            config.storage = StorageConfig(**data["storage"])
        
        if "routing" in data:
            config.routing = RoutingConfig(**data["routing"])
        
        if "codebase" in data:
            config.codebase = CodebaseConfig(**data["codebase"])
        
        if "tools" in data:
            for tool_name, tool_data in data["tools"].items():
                config.tools[tool_name] = ToolConfig(**tool_data)
        
        return config

    def to_dict(self) -> dict:
        """Convert Config to dictionary"""
        result = {
            "storage": {
                "db_path": self.storage.db_path,
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
