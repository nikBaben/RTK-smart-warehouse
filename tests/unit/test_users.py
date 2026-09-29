from unittest.mock import AsyncMock
import pytest
from backend.schemas.user import UserCreateWithKeycloak, UserUpdate
from backend.service.user_service import UserService
from backend.service.auth_service import AuthService
from tests.fakes import Store, Users, Links, MemoryTransaction


@pytest.fixture
def scenario():
    store = Store()
    tx = MemoryTransaction(store)
    links = Links(store)
    service = UserService(
        Users(store), links, tx, password_hasher=lambda value: "hash:" + value
    )
    return store, tx, links, service


def registration():
    return UserCreateWithKeycloak(
        email="user@example.com", name="User", password="secret"
    )


async def test_user_and_identity_link_commit_together(scenario):
    store, tx, _, service = scenario
    user = await service.create_user_with_keycloak(registration(), "kk-1")
    assert store.links == {"kk-1": user.id}
    assert store.users[user.id].password_hash == "hash:secret"
    assert tx.commits == 1


async def test_link_failure_does_not_leave_orphan_user(scenario):
    store, tx, links, service = scenario
    links.fail = True
    with pytest.raises(RuntimeError, match="link insert"):
        await service.create_user_with_keycloak(registration(), "kk-1")
    assert not store.users and not store.links
    assert tx.commits == 0 and tx.rollbacks == 1


async def test_registration_compensates_keycloak_when_database_fails(scenario):
    store, tx, links, service = scenario
    links.fail = True
    identity = AsyncMock()
    identity.create_user.return_value = "kk-1"
    with pytest.raises(RuntimeError, match="link insert"):
        await service.register(registration(), identity)
    identity.delete_user.assert_awaited_once_with("kk-1")
    assert not store.users


async def test_password_hashing_belongs_to_service(scenario):
    store, tx, _, service = scenario
    user = await service.create_user_with_keycloak(registration(), "kk-1")
    await service.update_user(user.id, UserUpdate(password="new"))
    assert store.users[user.id].password_hash == "hash:new"
    assert not hasattr(store.users[user.id], "password")


async def test_repeat_login_reuses_user_and_link(scenario):
    store, _, _, service = scenario
    a = await service.get_or_create_user_from_keycloak(
        "kk-1", "user@example.com", {}, "secret"
    )
    b = await service.get_or_create_user_from_keycloak(
        "kk-1", "user@example.com", {}, "secret"
    )
    assert a.id == b.id and len(store.users) == 1 and len(store.links) == 1


async def test_existing_email_is_linked_without_duplicate(scenario):
    store, _, _, service = scenario
    user = await service.create_user_with_keycloak(registration(), "kk-1")
    linked = await service.get_or_create_user_from_keycloak(
        "kk-2", user.email, {}, "secret"
    )
    assert linked.id == user.id and len(store.users) == 1


async def test_refresh_response_keeps_email(scenario):
    _, _, _, users = scenario
    await users.create_user_with_keycloak(registration(), "kk-1")
    identity = AsyncMock()
    identity.refresh_token.return_value = {"access_token": "new-token"}
    identity.get_user_info.return_value = {"sub": "kk-1"}
    response = await AuthService(identity, users).refresh_token("refresh")
    assert response.token == "new-token"
    assert response.user.email == "user@example.com"
