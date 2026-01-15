"""
Pytest configuration and fixtures.
"""

import pytest
from rest_framework.test import APIClient

from apps.transactions.tests.factories import UserFactory, AdminUserFactory


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def user():
    """Create and return a regular user."""
    return UserFactory()


@pytest.fixture
def admin_user():
    """Create and return an admin user."""
    return AdminUserFactory()


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an admin-authenticated API client."""
    api_client.force_authenticate(user=admin_user)
    return api_client
