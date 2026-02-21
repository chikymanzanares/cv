import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from app.application.chat.create_thread import CreateThreadUseCase, CreateThreadResult
from app.domain.chat.entities import Thread
from app.domain.chat.repositories.thread_repository import ThreadRepository


class TestCreateThreadUseCase:
    def test_execute_creates_thread_successfully(self):
        # Arrange
        user_id = 1
        thread_id = uuid.uuid4()
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.create_thread.return_value = thread
        
        use_case = CreateThreadUseCase(thread_repo=thread_repo)
        
        # Act
        result = use_case.execute(user_id=user_id)
        
        # Assert
        assert isinstance(result, CreateThreadResult)
        assert result.thread_id == str(thread_id)
        thread_repo.create_thread.assert_called_once_with(user_id=user_id)
    
    def test_execute_creates_thread_for_different_user(self):
        # Arrange
        user_id = 42
        thread_id = uuid.uuid4()
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.create_thread.return_value = thread
        
        use_case = CreateThreadUseCase(thread_repo=thread_repo)
        
        # Act
        result = use_case.execute(user_id=user_id)
        
        # Assert
        assert result.thread_id == str(thread_id)
        thread_repo.create_thread.assert_called_once_with(user_id=user_id)
