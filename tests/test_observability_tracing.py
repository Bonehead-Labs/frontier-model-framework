"""Tests for FMF observability tracing functionality."""

import unittest
from unittest.mock import patch, MagicMock

from src.fmf.observability.tracing import (
    FMFTracer, 
    get_tracer, 
    trace_operation, 
    add_trace_event, 
    set_trace_attribute,
    is_tracing_enabled,
    enable_tracing,
    disable_tracing
)


class TestFMFTracer(unittest.TestCase):
    """Test FMFTracer functionality."""
    
    def setUp(self):
        """Set up test tracer."""
        self.tracer = FMFTracer(enabled=False)
    
    def test_tracer_initialization_disabled(self):
        """Test tracer initialization when disabled."""
        tracer = FMFTracer(enabled=False)
        self.assertFalse(tracer.enabled)
        self.assertIsNone(tracer.tracer)
    
    @patch('src.fmf.observability.tracing.OPENTELEMETRY_AVAILABLE', False)
    def test_tracer_initialization_no_opentelemetry(self):
        """Test tracer initialization when OpenTelemetry is not available."""
        tracer = FMFTracer(enabled=True)
        self.assertFalse(tracer.enabled)
        self.assertIsNone(tracer.tracer)
    
    def test_span_context_manager_disabled(self):
        """Test span context manager when tracing is disabled."""
        with self.tracer.span("test_span", {"key": "value"}):
            # Should not raise any exceptions
            pass
    
    def test_add_event_disabled(self):
        """Test add_event when tracing is disabled."""
        # Should not raise any exceptions
        self.tracer.add_event("test_event", {"key": "value"})
    
    def test_set_attribute_disabled(self):
        """Test set_attribute when tracing is disabled."""
        # Should not raise any exceptions
        self.tracer.set_attribute("key", "value")


class TestTracingIntegration(unittest.TestCase):
    """Test tracing integration functions."""
    
    def test_get_tracer(self):
        """Test get_tracer function."""
        tracer = get_tracer(enabled=False)
        self.assertIsInstance(tracer, FMFTracer)
        self.assertFalse(tracer.enabled)
    
    def test_get_tracer_singleton(self):
        """Test that get_tracer returns singleton."""
        tracer1 = get_tracer(enabled=False)
        tracer2 = get_tracer(enabled=False)
        self.assertIs(tracer1, tracer2)
    
    def test_trace_operation_decorator(self):
        """Test trace_operation decorator."""
        tracer = get_tracer(enabled=False)
        
        @trace_operation("test_operation", {"key": "value"})
        def test_function():
            return "test_result"
        
        # Should not raise any exceptions
        result = test_function()
        self.assertEqual(result, "test_result")
    
    def test_add_trace_event(self):
        """Test add_trace_event function."""
        # Should not raise any exceptions
        add_trace_event("test_event", {"key": "value"})
    
    def test_set_trace_attribute(self):
        """Test set_trace_attribute function."""
        # Should not raise any exceptions
        set_trace_attribute("key", "value")
    
    def test_is_tracing_enabled(self):
        """Test is_tracing_enabled function."""
        tracer = get_tracer(enabled=False)
        self.assertFalse(is_tracing_enabled())
    
    def test_enable_tracing(self):
        """Test enable_tracing function."""
        enable_tracing("test_service")
        tracer = get_tracer()
        # The tracer should be enabled after calling enable_tracing (if OpenTelemetry is available)
        # If OpenTelemetry is not available, the tracer will be disabled
        self.assertEqual(tracer.service_name, "test_service")
        # Note: tracer.enabled will be False if OpenTelemetry is not available
    
    def test_disable_tracing(self):
        """Test disable_tracing function."""
        disable_tracing()
        tracer = get_tracer()
        self.assertFalse(tracer.enabled)


class TestTracingWithOpenTelemetry(unittest.TestCase):
    """Test tracing with OpenTelemetry (mocked)."""
    
    def setUp(self):
        """Set up test with mocked OpenTelemetry."""
        self.opentelemetry_patcher = patch('src.fmf.observability.tracing.OPENTELEMETRY_AVAILABLE', True)
        self.opentelemetry_patcher.start()
        
        # Mock OpenTelemetry modules
        self.trace_patcher = patch('src.fmf.observability.tracing.trace')
        self.status_patcher = patch('src.fmf.observability.tracing.Status')
        self.status_code_patcher = patch('src.fmf.observability.tracing.StatusCode')
        self.tracer_provider_patcher = patch('src.fmf.observability.tracing.TracerProvider')
        self.batch_span_processor_patcher = patch('src.fmf.observability.tracing.BatchSpanProcessor')
        self.console_span_exporter_patcher = patch('src.fmf.observability.tracing.ConsoleSpanExporter')
        self.resource_patcher = patch('src.fmf.observability.tracing.Resource')
        
        self.mock_trace = self.trace_patcher.start()
        self.mock_status = self.status_patcher.start()
        self.mock_status_code = self.status_code_patcher.start()
        self.mock_tracer_provider = self.tracer_provider_patcher.start()
        self.mock_batch_span_processor = self.batch_span_processor_patcher.start()
        self.mock_console_span_exporter = self.console_span_exporter_patcher.start()
        self.mock_resource = self.resource_patcher.start()
        
        # Set up mocks
        self.mock_trace.get_tracer.return_value = MagicMock()
        self.mock_trace.set_tracer_provider.return_value = None
        self.mock_trace.get_current_span.return_value = MagicMock()
        self.mock_trace.get_current_span.return_value.is_recording.return_value = True
        self.mock_trace.get_current_span.return_value.add_event.return_value = None
        self.mock_trace.get_current_span.return_value.set_attribute.return_value = None
    
    def tearDown(self):
        """Clean up patches."""
        self.opentelemetry_patcher.stop()
        self.trace_patcher.stop()
        self.status_patcher.stop()
        self.status_code_patcher.stop()
        self.tracer_provider_patcher.stop()
        self.batch_span_processor_patcher.stop()
        self.console_span_exporter_patcher.stop()
        self.resource_patcher.stop()
    
    def test_tracer_initialization_with_opentelemetry(self):
        """Test tracer initialization with OpenTelemetry available."""
        tracer = FMFTracer(enabled=True, service_name="test_service")
        
        self.assertTrue(tracer.enabled)
        self.assertIsNotNone(tracer.tracer)
        self.assertEqual(tracer.service_name, "test_service")
    
    def test_span_context_manager_with_opentelemetry(self):
        """Test span context manager with OpenTelemetry."""
        tracer = FMFTracer(enabled=True, service_name="test_service")
        
        with tracer.span("test_span", {"key": "value"}):
            # Should not raise any exceptions
            pass
        
        # Verify tracer was used
        self.mock_trace.get_tracer.assert_called_once()
    
    def test_add_event_with_opentelemetry(self):
        """Test add_event with OpenTelemetry."""
        tracer = FMFTracer(enabled=True, service_name="test_service")
        
        tracer.add_event("test_event", {"key": "value"})
        
        # Verify current span was used
        self.mock_trace.get_current_span.assert_called()
    
    def test_set_attribute_with_opentelemetry(self):
        """Test set_attribute with OpenTelemetry."""
        tracer = FMFTracer(enabled=True, service_name="test_service")
        
        tracer.set_attribute("key", "value")
        
        # Verify current span was used
        self.mock_trace.get_current_span.assert_called()
    
    def test_span_exception_handling(self):
        """Test span exception handling."""
        tracer = FMFTracer(enabled=True, service_name="test_service")
        
        with self.assertRaises(ValueError):
            with tracer.span("test_span", {"key": "value"}):
                raise ValueError("Test error")
        
        # Verify status was set to error
        self.mock_status.assert_called()


if __name__ == "__main__":
    unittest.main()
