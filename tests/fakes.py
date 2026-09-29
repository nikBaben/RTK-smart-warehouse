"""Small stateful test adapters; no SQLAlchemy, Redis or Keycloak."""

from copy import deepcopy
from types import SimpleNamespace


class Store:
    def __init__(self):
        self.warehouses = {}
        self.products = {}
        self.users = {}
        self.links = {}
        self.records = []


class MemoryTransaction:
    def __init__(self, store):
        self.store = store
        self.commits = 0
        self.rollbacks = 0
        self.fail_commit = False

    async def __aenter__(self):
        self.before = deepcopy(self.store.__dict__)
        self.committed = False
        return self

    async def commit(self):
        if self.fail_commit:
            raise RuntimeError("storage unavailable")
        self.commits += 1
        self.committed = True

    async def __aexit__(self, exc_type, exc, traceback):
        if exc is not None or not self.committed:
            self.store.__dict__.update(self.before)
            self.rollbacks += 1
        return False


class Warehouses:
    def __init__(self, store):
        self.store = store

    async def lock_many(self, ids):
        return [
            self.store.warehouses[id]
            for id in sorted(ids)
            if id in self.store.warehouses
        ]

    async def get_by_id(self, id):
        return self.store.warehouses.get(id)

    async def set_products_count(self, id, count):
        self.store.warehouses[id].products_count = count


class Products:
    def __init__(self, store):
        self.store = store

    async def create(self, **values):
        product = SimpleNamespace(**values)
        self.store.products[product.id] = product
        return product

    async def get(self, id):
        return self.store.products.get(id)

    get_for_update = get

    async def edit(self, id, **values):
        product = self.store.products[id]
        product.__dict__.update(values)
        return product

    async def delete(self, id):
        del self.store.products[id]


class Users:
    def __init__(self, store):
        self.store = store

    async def get_by_kkid(self, kkid):
        return self.store.users.get(self.store.links.get(kkid))

    async def get_by_email(self, email):
        return next((u for u in self.store.users.values() if u.email == email), None)

    async def create(self, data):
        user = SimpleNamespace(id=len(self.store.users) + 1, **data.model_dump())
        self.store.users[user.id] = user
        return user

    async def update(self, id, data):
        user = self.store.users.get(id)
        if user is not None:
            user.__dict__.update(data)
        return user


class Links:
    def __init__(self, store):
        self.store = store
        self.fail = False

    async def create(self, kkid, user_id):
        if self.fail:
            raise RuntimeError("link insert failed")
        self.store.links[kkid] = user_id
