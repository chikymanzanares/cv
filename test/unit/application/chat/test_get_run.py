import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from app.application.chat.get_run import GetRunUseCase, GetRunResult
from app.domain.chat.entities import Run, RunStatus
from app.domain.chat.repositories.run_repository import RunRepository


class TestGetRunUseCase:
    def test_execute_returns_run_successfully(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        created_at = datetime.now()
        started_at = datetime.now()
        finished_at = datetime.now()
        
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.done,
            created_at=created_at,
            started_at=started_at,
            finished_at=finished_at,
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = GetRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert isinstance(result, GetRunResult)
        assert result.run_id == str(run_id)
        assert result.thread_id == str(thread_id)
        assert result.status == RunStatus.done.value
        assert result.created_at == created_at.isoformat()
        assert result.started_at == started_at.isoformat()
        assert result.finished_at == finished_at.isoformat()
        assert result.error is None
        run_repo.get_run.assert_called_once_with(run_id=run_id)
    
    def test_execute_raises_error_when_run_not_found(self):
        # Arrange
        run_id = uuid.uuid4()
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = None
        
        use_case = GetRunUseCase(run_repo=run_repo)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Run not found"):
            use_case.execute(run_id=run_id)
        
        run_repo.get_run.assert_called_once_with(run_id=run_id)
    
    def test_execute_handles_run_with_none_timestamps(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        created_at = datetime.now()
        
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.queued,
            created_at=created_at,
            started_at=None,
            finished_at=None,
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = GetRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.started_at is None
        assert result.finished_at is None
        assert result.created_at == created_at.isoformat()
    
    def test_execute_handles_run_with_error(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        error_message = "Something went wrong"
        
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.error,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=datetime.now(),
            error=error_message,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = GetRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.status == RunStatus.error.value
        assert result.error == error_message
    
    def test_execute_handles_all_run_statuses(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        
        for status in RunStatus:
            run = Run(
                id=run_id,
                thread_id=thread_id,
                status=status,
                created_at=datetime.now(),
                started_at=None,
                finished_at=None,
                error=None,
            )
            
            run_repo = Mock(spec=RunRepository)
            run_repo.get_run.return_value = run
            
            use_case = GetRunUseCase(run_repo=run_repo)
            
            # Act
            result = use_case.execute(run_id=run_id)
            
            # Assert
            assert result.status == status.value
