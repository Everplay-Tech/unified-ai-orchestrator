"""Test data generators"""

import pytest
import random
import string
from typing import List, Dict, Any
from datetime import datetime, timedelta


class DataGenerator:
    """Generate test data"""
    
    @staticmethod
    def random_string(length: int = 10) -> str:
        """Generate random string"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=length))
    
    @staticmethod
    def random_id(prefix: str = "") -> str:
        """Generate random ID"""
        return f"{prefix}{DataGenerator.random_string(8)}"
    
    @staticmethod
    def random_message(length: int = 50) -> str:
        """Generate random message"""
        words = ["hello", "world", "test", "message", "data", "example"]
        return " ".join(random.choices(words, k=length))
    
    @staticmethod
    def conversation_id() -> str:
        """Generate conversation ID"""
        return DataGenerator.random_id("conv-")
    
    @staticmethod
    def project_id() -> str:
        """Generate project ID"""
        return DataGenerator.random_id("proj-")
    
    @staticmethod
    def user_id() -> str:
        """Generate user ID"""
        return DataGenerator.random_id("user-")
    
    @staticmethod
    def timestamp(offset_days: int = 0) -> int:
        """Generate timestamp"""
        dt = datetime.now() + timedelta(days=offset_days)
        return int(dt.timestamp())
    
    @staticmethod
    def messages(count: int = 5) -> List[Dict[str, Any]]:
        """Generate list of messages"""
        messages = []
        for i in range(count):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({
                "role": role,
                "content": DataGenerator.random_message(),
                "timestamp": DataGenerator.timestamp(),
            })
        return messages
    
    @staticmethod
    def code_block(language: str = "python") -> str:
        """Generate code block"""
        if language == "python":
            return f"""
def {DataGenerator.random_string(8)}():
    '''{DataGenerator.random_message(10)}'''
    return {random.randint(1, 100)}
"""
        elif language == "rust":
            return f"""
fn {DataGenerator.random_string(8)}() -> i32 {{
    {random.randint(1, 100)}
}}
"""
        else:
            return f"// {DataGenerator.random_message()}"


@pytest.fixture
def data_generator():
    """Data generator fixture"""
    return DataGenerator
