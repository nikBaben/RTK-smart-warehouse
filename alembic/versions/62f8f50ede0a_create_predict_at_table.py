"""create predict_at table

Revision ID: 62f8f50ede0a
Revises: da4573cb9f66
Create Date: 2025-10-31 22:51:12.248720

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '62f8f50ede0a'
down_revision: Union[str, Sequence[str], None] = 'da4573cb9f66'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
