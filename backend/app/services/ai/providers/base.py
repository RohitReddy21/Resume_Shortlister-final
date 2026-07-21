from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[list[dict]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Chat with the AI and return a streaming response.
        
        Args:
            system_prompt: System prompt to set context
            user_message: User's current message
            conversation_history: Optional list of previous messages, each with "role" and "content"
        
        Yields:
            Chunks of the AI's response
        """
        pass