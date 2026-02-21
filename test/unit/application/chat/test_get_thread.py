import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from app.application.chat.get_thread import GetThreadUseCase, GetThreadResult, ThreadMessageDTO
from app.domain.chat.entities import Thread, Message
from app.domain.chat.repositories.thread_repository import ThreadRepository


class TestGetThreadUseCase:
    def test_execute_returns_thread_with_messages(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        message1 = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content="Hello",
            created_at=datetime.now(),
        )
        message2 = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="assistant",
            content="Hi there!",
            created_at=datetime.now(),
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.list_messages.return_value = [message1, message2]
        
        use_case = GetThreadUseCase(thread_repo=thread_repo)
        
        # Act
        result = use_case.execute(thread_id=thread_id)
        
        # Assert
        assert isinstance(result, GetThreadResult)
        assert result.thread_id == str(thread_id)
        assert result.user_id == user_id
        assert len(result.messages) == 2
        assert isinstance(result.messages[0], ThreadMessageDTO)
        assert result.messages[0].id == str(message1.id)
        assert result.messages[0].role == "user"
        assert result.messages[0].content == "Hello"
        assert isinstance(result.messages[1], ThreadMessageDTO)
        assert result.messages[1].id == str(message2.id)
        assert result.messages[1].role == "assistant"
        assert result.messages[1].content == "Hi there!"
        
        thread_repo.get_thread.assert_called_once_with(thread_id=thread_id)
        thread_repo.list_messages.assert_called_once_with(thread_id=thread_id)
    
    def test_execute_returns_thread_without_messages(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.list_messages.return_value = []
        
        use_case = GetThreadUseCase(thread_repo=thread_repo)
        
        # Act
        result = use_case.execute(thread_id=thread_id)
        
        # Assert
        assert result.thread_id == str(thread_id)
        assert result.user_id == user_id
        assert len(result.messages) == 0
    
    def test_execute_raises_error_when_thread_not_found(self):
        # Arrange
        thread_id = uuid.uuid4()
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = None
        
        use_case = GetThreadUseCase(thread_repo=thread_repo)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Thread not found"):
            use_case.execute(thread_id=thread_id)
        
        thread_repo.get_thread.assert_called_once_with(thread_id=thread_id)
        thread_repo.list_messages.assert_not_called()
    
    def test_execute_formats_message_timestamps_correctly(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        created_at = datetime(2024, 1, 15, 10, 30, 45)
        message = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content="Test",
            created_at=created_at,
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.list_messages.return_value = [message]
        
        use_case = GetThreadUseCase(thread_repo=thread_repo)
        
        # Act
        result = use_case.execute(thread_id=thread_id)
        
        # Assert
        assert result.messages[0].created_at == created_at.isoformat()
