"""add unique constraints for authors and book_authors

Revision ID: 0002_add_unique_constraints
Revises: 8f3ceed17b25
Create Date: 2025-09-14

"""
from alembic import op
import sqlalchemy as sa
from typing import Union, Sequence

# revision identifiers, used by Alembic.
revision = "0002_add_unique_constraints"
down_revision: Union[str, Sequence[str], None] = "8f3ceed17b25"
branch_labels = None
depends_on = None


def upgrade() -> None:

    op.create_index(op.f("ix_authors_name"), "authors", ["name"], unique=True)

    op.create_unique_constraint(op.f("uq_book_authors_pair"), "book_authors", ["book_id", "author_id"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_book_authors_pair"), "book_authors", type_="unique")
    op.drop_index(op.f("ix_authors_name"), table_name="authors")
