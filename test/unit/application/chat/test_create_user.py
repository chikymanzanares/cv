from unittest.mock import Mock

from app.application.chat.create_user import CreateUserUseCase, CreateUserResult
from app.domain.chat.entities import User
from app.domain.chat.repositories.user_repository import UserRepository


class TestCreateUserUseCase:
    def test_execute_creates_user_with_name(self):
        # Arrange
        user_id = 1
        name = "John Doe"
        user = User(id=user_id, name=name)
        
        user_repo = Mock(spec=UserRepository)
        user_repo.create_user.return_value = user
        
        use_case = CreateUserUseCase(user_repo=user_repo)
        
        # Act
        result = use_case.execute(name=name)
        
        # Assert
        assert isinstance(result, CreateUserResult)
        assert result.user_id == user_id
        assert result.name == name
        user_repo.create_user.assert_called_once_with(name=name)
    
    def test_execute_creates_user_with_empty_name(self):
        # Arrange
        user_id = 2
        name = ""
        user = User(id=user_id, name=name)
        
        user_repo = Mock(spec=UserRepository)
        user_repo.create_user.return_value = user
        
        use_case = CreateUserUseCase(user_repo=user_repo)
        
        # Act
        result = use_case.execute(name=name)
        
        # Assert
        assert result.user_id == user_id
        assert result.name == name
    
    def test_execute_creates_user_with_long_name(self):
        # Arrange
        user_id = 3
        name = "A" * 100
        user = User(id=user_id, name=name)
        
        user_repo = Mock(spec=UserRepository)
        user_repo.create_user.return_value = user
        
        use_case = CreateUserUseCase(user_repo=user_repo)
        
        # Act
        result = use_case.execute(name=name)
        
        # Assert
        assert result.user_id == user_id
        assert result.name == name
