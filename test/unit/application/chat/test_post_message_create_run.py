import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from app.application.chat.post_message_create_run import PostMessageCreateRunUseCase, PostMessageCreateRunResult
from app.domain.chat.entities import Thread, Run, RunStatus, Message
from app.domain.chat.repositories.thread_repository import ThreadRepository
from app.domain.chat.repositories.run_repository import RunRepository


class TestPostMessageCreateRunUseCase:
    def test_execute_creates_message_and_run_successfully(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        content = "Hello, how are you?"
        
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        message = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content=content,
            created_at=datetime.now(),
        )
        
        run_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.queued,
            created_at=datetime.now(),
            started_at=None,
            finished_at=None,
            error=None,
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.add_user_message.return_value = message
        
        run_repo = Mock(spec=RunRepository)
        run_repo.create_run.return_value = run
        
        use_case = PostMessageCreateRunUseCase(
            thread_repo=thread_repo,
            run_repo=run_repo,
        )
        
        # Act
        result = use_case.execute(thread_id=thread_id, content=content)
        
        # Assert
        assert isinstance(result, PostMessageCreateRunResult)
        assert result.run_id == str(run_id)
        thread_repo.get_thread.assert_called_once_with(thread_id=thread_id)
        thread_repo.add_user_message.assert_called_once_with(thread_id=thread_id, content=content)
        run_repo.create_run.assert_called_once_with(thread_id=thread_id)
    
    def test_execute_raises_error_when_thread_not_found(self):
        # Arrange
        thread_id = uuid.uuid4()
        content = "Hello"
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = None
        
        run_repo = Mock(spec=RunRepository)
        
        use_case = PostMessageCreateRunUseCase(
            thread_repo=thread_repo,
            run_repo=run_repo,
        )
        
        # Act & Assert
        with pytest.raises(ValueError, match="Thread not found"):
            use_case.execute(thread_id=thread_id, content=content)
        
        thread_repo.get_thread.assert_called_once_with(thread_id=thread_id)
        thread_repo.add_user_message.assert_not_called()
        run_repo.create_run.assert_not_called()
    
    def test_execute_handles_empty_message_content(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        content = ""
        
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        message = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content=content,
            created_at=datetime.now(),
        )
        
        run_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.queued,
            created_at=datetime.now(),
            started_at=None,
            finished_at=None,
            error=None,
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.add_user_message.return_value = message
        
        run_repo = Mock(spec=RunRepository)
        run_repo.create_run.return_value = run
        
        use_case = PostMessageCreateRunUseCase(
            thread_repo=thread_repo,
            run_repo=run_repo,
        )
        
        # Act
        result = use_case.execute(thread_id=thread_id, content=content)
        
        # Assert
        assert result.run_id == str(run_id)
        thread_repo.add_user_message.assert_called_once_with(thread_id=thread_id, content="")
    
    def test_execute_handles_long_message_content(self):
        # Arrange
        thread_id = uuid.uuid4()
        user_id = 1
        content = "A" * 1000
        
        thread = Thread(
            id=thread_id,
            user_id=user_id,
            created_at=datetime.now(),
        )
        
        message = Message(
            id=uuid.uuid4(),
            thread_id=thread_id,
            role="user",
            content=content,
            created_at=datetime.now(),
        )
        
        run_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.queued,
            created_at=datetime.now(),
            started_at=None,
            finished_at=None,
            error=None,
        )
        
        thread_repo = Mock(spec=ThreadRepository)
        thread_repo.get_thread.return_value = thread
        thread_repo.add_user_message.return_value = message
        
        run_repo = Mock(spec=RunRepository)
        run_repo.create_run.return_value = run
        
        use_case = PostMessageCreateRunUseCase(
            thread_repo=thread_repo,
            run_repo=run_repo,
        )
        
        # Act
        result = use_case.execute(thread_id=thread_id, content=content)
        
        # Assert
        assert result.run_id == str(run_id)
        thread_repo.add_user_message.assert_called_once_with(thread_id=thread_id, content=content)
