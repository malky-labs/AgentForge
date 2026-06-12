from abc import ABC, abstractmethod
from typing import Type
from pydantic import BaseModel

class BaseTool(ABC):
    """Abstract base class that all custom python plugins / tools must inherit."""
    
    name: str
    description: str
    args_schema: Type[BaseModel]

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """Core execution logic. Must return a string response."""
        pass
