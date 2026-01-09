"""Setup script for unified-ai-orchestrator"""

from setuptools import setup, find_packages

setup(
    name="unified-ai-orchestrator",
    version="0.1.0",
    packages=find_packages(where="python-glue"),
    package_dir={"": "python-glue"},
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.5.0",
        "pydantic-settings>=2.1.0",
        "anthropic>=0.18.0",
        "openai>=1.12.0",
        "httpx>=0.25.0",
        "typer>=0.9.0",
        "rich>=13.7.0",
        "python-dotenv>=1.0.0",
        "keyring>=24.3.0",
        "toml>=0.10.2",
        "aiofiles>=23.2.0",
    ],
    entry_points={
        "console_scripts": [
            "uai=unified_ai.cli.main:app",
        ],
    },
)
