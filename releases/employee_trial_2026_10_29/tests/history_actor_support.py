"""Finite synthetic app-user records for repository-only audit tests."""
from types import SimpleNamespace


class MemoryUsers:
    def __init__(self, *identities):
        self.users = {identity: SimpleNamespace(user_id=identity, email=identity+'@example.invalid') for identity in identities}

    def get_user(self, identity):
        return self.users.get(identity)
