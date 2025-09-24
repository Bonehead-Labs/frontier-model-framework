# ADR-001: SDK-First Design with Fluent Builder API

## Status
Accepted

## Context
The Frontier Model Framework (FMF) currently provides multiple interfaces:
- CLI commands for operations and orchestration
- Recipe-based YAML configuration for declarative workflows  
- Python SDK with convenience methods for common operations

While all interfaces work well, the current documentation and examples lead with CLI/recipes, making the Python SDK feel secondary. For developer adoption and integration scenarios, a fluent, object-oriented API should be the primary interface.

## Decision
Introduce a fluent builder API as the primary interface while maintaining full backward compatibility with existing CLI and recipe workflows.

### Core Design Principles
1. **Fluent Builder Pattern**: Methods return `self` to enable method chaining
2. **Progressive Configuration**: Start with sensible defaults, override as needed
3. **Non-Breaking**: All existing APIs remain unchanged
4. **Stub-First**: Initial implementation provides working stubs that delegate to existing internals

### API Design
```python
# Primary interface - fluent builder
fmf = (FMF.from_env("fmf.yaml")
       .with_service("azure_openai")
       .with_rag(enabled=True, pipeline="documents")
       .with_response("csv"))

# Convenience methods that use the builder internally
records = fmf.csv_analyse(
    input="./data/comments.csv",
    text_col="Comment", 
    id_col="ID",
    prompt="Summarize this comment"
)
```

## Scope

### In Scope
- Fluent builder API skeleton with method chaining
- Documentation reordering to lead with SDK examples
- Lightweight unit tests for API contract validation
- Demo script showing fluent API usage
- All methods as no-op stubs that compile and return appropriate types

### Out of Scope (Future Iterations)
- Heavy refactoring of internal implementation
- Breaking changes to existing APIs
- Advanced fluent API features (validation, type safety improvements)
- Performance optimizations

## Compatibility Strategy

### Backward Compatibility
- All existing imports continue to work: `from fmf.sdk import FMF, run_recipe_simple`
- CLI commands unchanged
- Recipe YAML format unchanged
- Existing method signatures preserved

### Migration Path
1. **Phase 1** (Current): Add fluent API alongside existing methods
2. **Phase 2** (Future): Gradually migrate internal implementations to use fluent builder
3. **Phase 3** (Future): Consider deprecation warnings for non-fluent patterns (with long lead time)

## Implementation Plan

### Deliverables
1. **ADR Document**: This document
2. **Fluent API Skeleton**: `FMF` class with chaining methods
3. **Unit Tests**: Smoke tests for API contract validation
4. **Documentation**: README reordered to show SDK first
5. **Demo Script**: `analyse_csv_sdk.py` using only fluent API

### Method Signatures (Stubs)
```python
class FMF:
    @classmethod
    def from_env(cls, path: str | None = None) -> "FMF"
    
    def with_service(self, name: str) -> "FMF"
    def with_rag(self, enabled: bool, pipeline: str | None = None) -> "FMF" 
    def with_response(self, kind: Literal["csv","json","text"]) -> "FMF"
    def with_source(self, connector: str, **kwargs) -> "FMF"
    def run_inference(self, kind: str, method: str, **kwargs) -> Any
    
    # Convenience wrappers (existing methods, now documented as primary)
    def csv_analyse(self, **kwargs) -> List[Dict[str, Any]] | None
    def text_to_json(self, **kwargs) -> List[Dict[str, Any]] | None
```

## Non-Goals
- Complete implementation of all fluent methods (stubs only)
- Breaking existing functionality
- Complex validation or type checking in fluent API
- Performance optimizations
- Advanced error handling in fluent layer

## Consequences

### Positive
- Clearer developer experience with object-oriented API
- Better discoverability through method chaining
- Maintains all existing functionality
- Sets foundation for future enhancements

### Negative
- Additional API surface area to maintain
- Potential confusion between fluent and non-fluent patterns
- Stub implementations may not be immediately useful

### Risks
- **Mitigation**: Clear documentation about stub nature
- **Mitigation**: Existing APIs remain fully functional
- **Mitigation**: Gradual implementation plan

## References
- Current FMF architecture: `docs/deepdive/ARCHITECTURE.md`
- Existing SDK: `src/fmf/sdk/client.py`
- Fluent Builder Pattern: https://en.wikipedia.org/wiki/Fluent_interface
