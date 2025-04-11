"""Initial migration

Revision ID: 345496061a53
Revises: 
Create Date: 2025-04-04 13:13:50.842192

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd0841f3d03b1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the 'users' table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('username', sa.String, nullable=False, unique=True, index=True),
        sa.Column('email', sa.String, nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('full_name', sa.String, nullable=True, index=True),
        sa.Column('balance', sa.Float(precision=10, decimal_return_scale=2), nullable=False, server_default='0.0'),
        sa.Column('is_active', sa.Boolean, nullable=True, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean, nullable=True, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create ENUM for BookAvailability
    bookavailability_enum = sa.Enum('available', 'in_progress', 'not_available', name='bookavailability')
    # bookavailability_enum.create(op.get_bind(), checkfirst=True)

    # Create the 'books' table
    op.create_table(
        'books',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('title', sa.String, nullable=False, index=True),
        sa.Column('author', sa.String, nullable=False, index=True),
        sa.Column('genre', sa.String, nullable=True, index=True),
        sa.Column('pages', sa.Integer, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('cost', sa.Float(precision=10, decimal_return_scale=2), nullable=False),
        sa.Column('language', sa.String, nullable=True),
        sa.Column('availability_status', bookavailability_enum, nullable=False, server_default="available"),
        sa.Column('publication_date', sa.Date, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True)
    )

    # Create the many-to-many association table for user favorite books
    op.create_table(
        'user_favorite_books',
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id'), primary_key=True)
    )

    # Create ENUM for PurchaseStatus
    purchasestatus_enum = sa.Enum('in_cart', 'pending', 'completed', 'failed', 'cancelled', name='purchasestatus')
    # purchasestatus_enum.create(op.get_bind(), checkfirst=True)

    # Create the 'purchases' table
    op.create_table(
        'purchases',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id'), nullable=False),
        sa.Column('purchase_date', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('status', purchasestatus_enum, nullable=False, server_default="in_cart"),
        sa.Column('cost_at_purchase', sa.Float(precision=10, decimal_return_scale=2), nullable=False)
    )

    # Create the 'comments' table
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('text', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id'), nullable=False)
    )

    # Create the 'ratings' table with a unique constraint on (user_id, book_id)
    op.create_table(
        'ratings',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('score', sa.Integer, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('book_id', sa.Integer, sa.ForeignKey('books.id'), nullable=False),
        sa.UniqueConstraint('user_id', 'book_id', name='_user_book_uc')
    )


def downgrade() -> None:
    # Drop the 'ratings' table
    op.drop_table('ratings')
    # Drop the 'comments' table
    op.drop_table('comments')
    # Drop the 'purchases' table
    op.drop_table('purchases')
    # Drop the association table for user favorite books
    op.drop_table('user_favorite_books')
    # Drop the 'books' table
    op.drop_table('books')
    # Drop ENUM for BookAvailability
    bookavailability_enum = sa.Enum(name='bookavailability')
    bookavailability_enum.drop(op.get_bind(), checkfirst=True)
    # Drop the 'users' table
    op.drop_table('users')
    # Drop ENUM for PurchaseStatus
    purchasestatus_enum = sa.Enum(name='purchasestatus')
    purchasestatus_enum.drop(op.get_bind(), checkfirst=True)
    pass
