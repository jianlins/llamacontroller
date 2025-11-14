# 8. Testing Best Practices

Effective testing ensures LlamaController is reliable and maintainable.

## Recommended Framework

- Use `pytest` for all tests
- Organize tests in the `tests/` directory

## Test Types

### Unit Tests

- Test individual components (e.g., config manager, lifecycle manager)
- Use assertions to verify expected behavior

### Integration Tests

- Test interactions between components (e.g., model loading, API calls)
- Use fixtures for setup and teardown

### End-to-End Tests

- Simulate real user workflows via API and Web UI
- Verify complete system behavior

## Coverage Goals

- Aim for 80%+ unit test coverage
- Cover all major workflows with integration and E2E tests

## Example Test Case

```python
def test_load_model(config_manager):
    result = config_manager.load_model("phi-4-reasoning")
    assert result.success
```

## Running Tests

```bash
pytest
pytest --cov=src/llamacontroller --cov-report=html
```

## Continuous Integration

- Run tests on every commit and pull request
- Use GitHub Actions or similar CI tools

## Common Pitfalls

- Avoid print-only scripts; always use assertions
- Do not depend on external state or global config
- Use fixtures for reusable setup

## Troubleshooting Tests

- Check logs for failed tests
- Mock external dependencies as needed

---
