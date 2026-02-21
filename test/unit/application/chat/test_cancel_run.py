import uuid
from datetime import datetime
from unittest.mock import Mock

import pytest

from app.application.chat.cancel_run import CancelRunUseCase, CancelRunResult
from app.domain.chat.entities import Run, RunStatus
from app.domain.chat.repositories.run_repository import RunRepository


class TestCancelRunUseCase:
    def test_execute_cancels_running_run(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.running,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=None,
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        run_repo.set_status = Mock()
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert isinstance(result, CancelRunResult)
        assert result.status == RunStatus.canceled.value
        run_repo.get_run.assert_called_once_with(run_id=run_id)
        run_repo.set_status.assert_called_once_with(run_id=run_id, status=RunStatus.canceled)
    
    def test_execute_raises_error_when_run_not_found(self):
        # Arrange
        run_id = uuid.uuid4()
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = None
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Run not found"):
            use_case.execute(run_id=run_id)
        
        run_repo.get_run.assert_called_once_with(run_id=run_id)
        run_repo.set_status.assert_not_called()
    
    def test_execute_is_idempotent_for_done_run(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.done,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=datetime.now(),
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.status == RunStatus.done.value
        run_repo.get_run.assert_called_once_with(run_id=run_id)
        run_repo.set_status.assert_not_called()
    
    def test_execute_is_idempotent_for_error_run(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.error,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=datetime.now(),
            error="Some error",
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.status == RunStatus.error.value
        run_repo.get_run.assert_called_once_with(run_id=run_id)
        run_repo.set_status.assert_not_called()
    
    def test_execute_is_idempotent_for_already_canceled_run(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.canceled,
            created_at=datetime.now(),
            started_at=datetime.now(),
            finished_at=None,
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.status == RunStatus.canceled.value
        run_repo.get_run.assert_called_once_with(run_id=run_id)
        run_repo.set_status.assert_not_called()
    
    def test_execute_cancels_queued_run(self):
        # Arrange
        run_id = uuid.uuid4()
        thread_id = uuid.uuid4()
        run = Run(
            id=run_id,
            thread_id=thread_id,
            status=RunStatus.queued,
            created_at=datetime.now(),
            started_at=None,
            finished_at=None,
            error=None,
        )
        
        run_repo = Mock(spec=RunRepository)
        run_repo.get_run.return_value = run
        run_repo.set_status = Mock()
        
        use_case = CancelRunUseCase(run_repo=run_repo)
        
        # Act
        result = use_case.execute(run_id=run_id)
        
        # Assert
        assert result.status == RunStatus.canceled.value
        run_repo.set_status.assert_called_once_with(run_id=run_id, status=RunStatus.canceled)
