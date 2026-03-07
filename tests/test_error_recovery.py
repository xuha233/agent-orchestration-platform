# -*- coding: utf-8 -*-
"""Tests for Error Recovery"""

import pytest
import time
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.aop.agent.error_recovery import (
    ErrorType,
    RecoveryAction,
    RecoveryDecision,
    ErrorContext,
    RetryState,
    ErrorClassifier,
    RecoveryStrategy,
    ErrorRecoveryManager,
    RecoveryCompletedException,
    CheckpointManager,
)


class TestErrorType:
    """Tests for ErrorType enum"""
    
    def test_error_types(self):
        """Test error type values"""
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.NETWORK.value == "network"
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.UNKNOWN.value == "unknown"


class TestRecoveryAction:
    """Tests for RecoveryAction enum"""
    
    def test_recovery_actions(self):
        """Test recovery action values"""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.SKIP.value == "skip"
        assert RecoveryAction.ESCALATE.value == "escalate"


class TestRecoveryDecision:
    """Tests for RecoveryDecision"""
    
    def test_decision_creation(self):
        """Test creating decision"""
        decision = RecoveryDecision(
            action=RecoveryAction.RETRY,
            reason="Test reason",
            params={"key": "value"},
            delay_seconds=1.0,
        )
        assert decision.action == RecoveryAction.RETRY
        assert decision.reason == "Test reason"
    
    def test_decision_defaults(self):
        """Test decision defaults"""
        decision = RecoveryDecision(
            action=RecoveryAction.SKIP,
            reason="Skip",
        )
        assert decision.params == {}
        assert decision.delay_seconds == 0.0
        assert decision.max_retries == 3


class TestErrorContext:
    """Tests for ErrorContext"""
    
    def test_context_creation(self):
        """Test creating error context"""
        error = ValueError("Test error")
        ctx = ErrorContext(
            error=error,
            error_type=ErrorType.VALIDATION,
            retry_count=1,
            task_id="task-001",
        )
        assert ctx.error_type == ErrorType.VALIDATION
        assert ctx.retry_count == 1
    
    def test_context_to_dict(self):
        """Test context serialization"""
        ctx = ErrorContext(
            error=ValueError("Test"),
            error_type=ErrorType.TIMEOUT,
            retry_count=2,
            task_id="task-001",
        )
        data = ctx.to_dict()
        
        assert data["error_type"] == "timeout"
        assert data["retry_count"] == 2
        assert data["task_id"] == "task-001"


class TestRetryState:
    """Tests for RetryState"""
    
    def test_initial_state(self):
        """Test initial retry state"""
        state = RetryState()
        assert state.attempt == 0
        assert state.can_retry() is True
    
    def test_next_delay_exponential(self):
        """Test exponential backoff delay"""
        state = RetryState(base_delay=1.0, max_delay=60.0)
        
        state.attempt = 0
        delay0 = state.next_delay("exponential")
        
        state.attempt = 1
        delay1 = state.next_delay("exponential")
        
        state.attempt = 2
        delay2 = state.next_delay("exponential")
        
        # Exponential growth (approximately, due to jitter)
        assert delay0 < delay1 < delay2
    
    def test_next_delay_linear(self):
        """Test linear backoff delay"""
        state = RetryState(base_delay=1.0, max_delay=60.0)
        
        state.attempt = 0
        delay0 = state.next_delay("linear")
        
        state.attempt = 1
        delay1 = state.next_delay("linear")
        
        assert delay1 > delay0
    
    def test_max_delay_cap(self):
        """Test max delay cap"""
        state = RetryState(base_delay=10.0, max_delay=30.0)
        state.attempt = 10  # Very high attempt
        
        delay = state.next_delay("exponential")
        assert delay <= state.max_delay
    
    def test_can_retry(self):
        """Test retry limit"""
        state = RetryState(max_attempts=3)
        
        state.attempt = 0
        assert state.can_retry() is True
        
        state.attempt = 2
        assert state.can_retry() is True
        
        state.attempt = 3
        assert state.can_retry() is False


class TestErrorClassifier:
    """Tests for ErrorClassifier"""
    
    def test_classify_timeout(self):
        """Test classifying timeout errors"""
        classifier = ErrorClassifier()
        
        error = TimeoutError("Connection timed out")
        assert classifier.classify(error) == ErrorType.TIMEOUT
        
        error = Exception("operation timeout")
        assert classifier.classify(error) == ErrorType.TIMEOUT
    
    def test_classify_network(self):
        """Test classifying network errors"""
        classifier = ErrorClassifier()
        
        error = ConnectionError("Network unreachable")
        assert classifier.classify(error) == ErrorType.NETWORK
        
        error = Exception("connection refused")
        assert classifier.classify(error) == ErrorType.NETWORK
    
    def test_classify_rate_limit(self):
        """Test classifying rate limit errors"""
        classifier = ErrorClassifier()
        
        error = Exception("Rate limit exceeded")
        assert classifier.classify(error) == ErrorType.RATE_LIMIT
        
        error = Exception("429 Too Many Requests")
        assert classifier.classify(error) == ErrorType.RATE_LIMIT
    
    def test_classify_validation(self):
        """Test classifying validation errors"""
        classifier = ErrorClassifier()
        
        error = Exception("Validation failed")
        assert classifier.classify(error) == ErrorType.VALIDATION
    
    def test_classify_permission(self):
        """Test classifying permission errors"""
        classifier = ErrorClassifier()
        
        error = PermissionError("Access denied")
        assert classifier.classify(error) == ErrorType.PERMISSION
    
    def test_classify_unknown(self):
        """Test classifying unknown errors"""
        classifier = ErrorClassifier()
        
        error = Exception("Some random error")
        assert classifier.classify(error) == ErrorType.UNKNOWN


class TestRecoveryStrategy:
    """Tests for RecoveryStrategy"""
    
    def test_strategy_creation(self):
        """Test creating strategy"""
        strategy = RecoveryStrategy(max_retries=5, base_delay=2.0)
        assert strategy.max_retries == 5
        assert strategy.base_delay == 2.0
    
    def test_decide_timeout_with_high_progress(self):
        """Test timeout with high progress"""
        strategy = RecoveryStrategy()
        
        ctx = ErrorContext(
            error=TimeoutError(),
            error_type=ErrorType.TIMEOUT,
        )
        
        decision = strategy.decide(ctx, task_progress=0.95)
        assert decision.action == RecoveryAction.MARK_COMPLETED
    
    def test_decide_timeout_with_medium_progress(self):
        """Test timeout with medium progress"""
        strategy = RecoveryStrategy()
        
        ctx = ErrorContext(
            error=TimeoutError(),
            error_type=ErrorType.TIMEOUT,
        )
        
        decision = strategy.decide(ctx, task_progress=0.6)
        assert decision.action == RecoveryAction.RETRY
    
    def test_decide_network_error(self):
        """Test network error handling"""
        strategy = RecoveryStrategy()
        
        ctx = ErrorContext(
            error=ConnectionError(),
            error_type=ErrorType.NETWORK,
        )
        
        decision = strategy.decide(ctx)
        assert decision.action == RecoveryAction.RETRY_WITH_BACKOFF
    
    def test_decide_rate_limit(self):
        """Test rate limit handling"""
        strategy = RecoveryStrategy()
        
        ctx = ErrorContext(
            error=Exception("Rate limit"),
            error_type=ErrorType.RATE_LIMIT,
        )
        
        decision = strategy.decide(ctx)
        assert decision.action == RecoveryAction.RETRY_WITH_BACKOFF
        assert decision.delay_seconds == 5.0
    
    def test_decide_permission_error(self):
        """Test permission error handling"""
        strategy = RecoveryStrategy()
        
        ctx = ErrorContext(
            error=PermissionError(),
            error_type=ErrorType.PERMISSION,
        )
        
        decision = strategy.decide(ctx)
        assert decision.action == RecoveryAction.ESCALATE


class TestErrorRecoveryManager:
    """Tests for ErrorRecoveryManager"""
    
    def test_manager_creation(self):
        """Test creating manager"""
        manager = ErrorRecoveryManager()
        assert manager.classifier is not None
        assert manager.strategy is not None
    
    def test_execute_success(self):
        """Test successful execution"""
        manager = ErrorRecoveryManager()
        
        result = manager.execute_with_recovery(
            func=lambda: "success",
            task_id="test",
        )
        
        assert result == "success"
    
    def test_execute_with_retry(self):
        """Test execution with retry"""
        manager = ErrorRecoveryManager(max_retries=3)
        
        call_count = [0]
        
        def flaky_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ConnectionError("Network error")
            return "success"
        
        result = manager.execute_with_recovery(
            func=flaky_func,
            task_id="test",
        )
        
        assert result == "success"
        assert call_count[0] == 3
    
    def test_execute_max_retries_exceeded(self):
        """Test max retries exceeded"""
        manager = ErrorRecoveryManager(max_retries=2, base_delay=0.1)
        
        call_count = [0]
        
        def always_fail():
            call_count[0] += 1
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            manager.execute_with_recovery(
                func=always_fail,
                task_id="test",
            )
        
        assert call_count[0] >= 2  # At least initial + retries
    
    def test_on_retry_callback(self):
        """Test retry callback"""
        manager = ErrorRecoveryManager(max_retries=5, base_delay=0.1)
        
        retries = []
        
        def flaky_func():
            if len(retries) < 2:
                raise ConnectionError("Network error")  # Use network error, not timeout
            return "success"
        
        result = manager.execute_with_recovery(
            func=flaky_func,
            task_id="test",
            on_retry=lambda attempt, err: retries.append(attempt),
        )
        
        assert result == "success"
        assert len(retries) == 2
    
    def test_get_error_stats(self):
        """Test error statistics"""
        manager = ErrorRecoveryManager(max_retries=1, base_delay=0.1)
        
        try:
            manager.execute_with_recovery(
                func=lambda: (_ for _ in ()).throw(ConnectionError()),
                task_id="test1",
            )
        except ConnectionError:
            pass
        
        try:
            manager.execute_with_recovery(
                func=lambda: (_ for _ in ()).throw(TimeoutError()),
                task_id="test2",
            )
        except TimeoutError:
            pass
        
        stats = manager.get_error_stats()
        
        assert stats["total_errors"] >= 2
        assert "by_type" in stats


class TestCheckpointManager:
    """Tests for CheckpointManager"""
    
    def test_checkpoint_creation(self, tmp_path):
        """Test creating checkpoint"""
        manager = CheckpointManager(
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        
        manager.save_checkpoint(
            task_id="task-001",
            state="running",
            progress=0.5,
            data={"key": "value"},
        )
        
        checkpoint = manager.load_checkpoint("task-001")
        assert checkpoint is not None
        assert checkpoint["state"] == "running"
        assert checkpoint["progress"] == 0.5
    
    def test_load_nonexistent_checkpoint(self, tmp_path):
        """Test loading nonexistent checkpoint"""
        manager = CheckpointManager(
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        
        checkpoint = manager.load_checkpoint("nonexistent")
        assert checkpoint is None
    
    def test_clear_checkpoint(self, tmp_path):
        """Test clearing checkpoint"""
        manager = CheckpointManager(
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        
        manager.save_checkpoint(
            task_id="task-001",
            state="running",
            progress=0.5,
            data={},
        )
        
        manager.clear_checkpoint("task-001")
        
        checkpoint = manager.load_checkpoint("task-001")
        assert checkpoint is None
    
    def test_should_auto_save(self, tmp_path):
        """Test auto save check"""
        manager = CheckpointManager(
            checkpoint_dir=str(tmp_path / "checkpoints"),
            auto_save_interval=1,  # 1 second
        )
        
        # Initially should save
        assert manager.should_auto_save() is True
        
        # After saving
        manager.save_checkpoint("test", "running", 0.5, {})
        assert manager.should_auto_save() is False
        
        # After interval
        time.sleep(1.1)
        assert manager.should_auto_save() is True
    
    def test_list_checkpoints(self, tmp_path):
        """Test listing checkpoints"""
        manager = CheckpointManager(
            checkpoint_dir=str(tmp_path / "checkpoints"),
        )
        
        manager.save_checkpoint("task-1", "running", 0.5, {})
        manager.save_checkpoint("task-2", "completed", 1.0, {})
        
        checkpoints = manager.list_checkpoints()
        
        assert len(checkpoints) == 2


