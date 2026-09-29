from collections.abc import Callable
from backend.core.security import get_password_hash
from backend.domain.errors import NotFound
from backend.ports import (
    UserRepository,
    KkidUserRepository,
    Transaction,
    IdentityProvider,
)
from backend.schemas.user import UserCreate, UserCreateWithKeycloak, UserUpdate


class UserService:
    def __init__(
        self,
        user_repo: UserRepository,
        kkid_user_repo: KkidUserRepository,
        transaction: Transaction,
        password_hasher: Callable[[str], str] = get_password_hash,
    ):
        self.user_repo = user_repo
        self.kkid_user_repo = kkid_user_repo
        self.transaction = transaction
        self.password_hasher = password_hasher

    async def get_or_create_user_from_keycloak(
        self, kkid: str, email: str, user_info: dict, password: str
    ):
        async with self.transaction:
            user = await self.user_repo.get_by_kkid(kkid)
            if user is not None:
                await self.transaction.commit()
                return user
            user = await self.user_repo.get_by_email(email)
            if user is None:
                roles = user_info.get("realm_access", {}).get("roles", [])
                # Explicit application roles; Keycloak system roles never become application permissions.
                role = "admin" if "admin" in roles else "user"
                user = await self.user_repo.create(
                    UserCreate(
                        email=email,
                        name=user_info.get("name")
                        or user_info.get("preferred_username")
                        or email,
                        role=role,
                        password_hash=self.password_hasher(password),
                    )
                )
            await self.kkid_user_repo.create(kkid, user.id)
            await self.transaction.commit()
            return user

    async def create_user_with_keycloak(
        self, user_create: UserCreateWithKeycloak, kkid: str
    ):
        async with self.transaction:
            user = await self.user_repo.create(
                UserCreate(
                    email=user_create.email,
                    name=user_create.name,
                    role=user_create.role,
                    password_hash=self.password_hasher(user_create.password),
                )
            )
            await self.kkid_user_repo.create(kkid, user.id)
            await self.transaction.commit()
            return user

    async def register(self, data: UserCreateWithKeycloak, identity: IdentityProvider):
        """SQL and Keycloak cannot share a transaction: compensate a failed local write."""
        kkid = await identity.create_user(
            email=data.email,
            password=data.password,
            first_name=data.name,
            last_name="",
            username=data.email,
        )
        try:
            return await self.create_user_with_keycloak(data, kkid)
        except Exception:
            try:
                await identity.delete_user(kkid)
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Keycloak compensation failed for user %s", kkid
                )
            raise

    async def get_user_by_kkid(self, kkid: str):
        return await self.user_repo.get_by_kkid(kkid)

    async def get_user_by_email(self, email: str):
        return await self.user_repo.get_by_email(email)

    async def get_user_by_id(self, user_id: int):
        return await self.user_repo.get_by_id(user_id)

    async def create_user(self, user_create: UserCreate):
        async with self.transaction:
            user = await self.user_repo.create(user_create)
            await self.transaction.commit()
            return user

    async def update_user(self, user_id: int, user_update: UserUpdate):
        changes = user_update.model_dump(exclude_unset=True, exclude_none=True)
        if "password" in changes:
            changes["password_hash"] = self.password_hasher(changes.pop("password"))
        async with self.transaction:
            user = await self.user_repo.update(user_id, changes)
            if user is None:
                raise NotFound("User not found")
            await self.transaction.commit()
            return user
