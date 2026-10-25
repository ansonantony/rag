"""add document_id to chat_sessions

Revision ID: 0002_add_doc_id_to_sess
Revises: 0001_initial_schema
Create Date: 2024-09-21 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by alembic.
revision = '0002_add_doc_id_to_sess'
down_revision = '0001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add document_id column to chat_sessions table (nullable for now)
    op.add_column('chat_sessions', sa.Column('document_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('documents.id'), nullable=True))
    # Create index on document_id for better query performance
    op.create_index('ix_chat_sessions_document_id', 'chat_sessions', ['document_id'])


def downgrade() -> None:
    # Drop index and column
    op.drop_index('ix_chat_sessions_document_id', table_name='chat_sessions')
    op.drop_column('chat_sessions', 'document_id')