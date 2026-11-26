"""The complete test suite is offline, even if the local shell has live settings."""
import pytest


@pytest.fixture(autouse=True)
def offline_provider_boundary(monkeypatch):
    from coordinator import openai_provider
    def deny_paid_transport(*args, **kwargs):
        raise AssertionError('Real provider transport is forbidden in automated tests.')
    monkeypatch.setattr(openai_provider, '_send', deny_paid_transport)
    monkeypatch.delenv('OPENAI_LIVE_ENABLED', raising=False)
    monkeypatch.delenv('PHASE6A_REFERENCE_APPROVED', raising=False)
    monkeypatch.setenv('CANDIDATE_PROVIDER', 'mock')
