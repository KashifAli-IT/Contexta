"""initial schema: documents, document_chunks, chat_messages

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-05

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("file_key", sa.String(length=1024), nullable=False),
        sa.Column("file_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "content_type",
            sa.String(length=128),
            nullable=False,
            server_default="application/pdf",
        ),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "PROCESSING",
                "READY",
                "FAILED",
                name="documentstatus",
                native_enum=False,
                length=16,
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("job_id", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("id", UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_project_id", "documents", ["project_id"])
    op.create_index(
        "ix_documents_project_created", "documents", ["project_id", "created_at"]
    )

    op.create_table(
        "document_chunks",
        sa.Column("parent_chunk_id", UUID, nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "is_table", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("embedding_id", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("char_start", sa.Integer(), nullable=True),
        sa.Column("char_end", sa.Integer(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("id", UUID, nullable=False),
        sa.Column("document_id", UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_chunks_document_id", "document_chunks", ["document_id"]
    )
    op.create_index(
        "ix_document_chunks_embedding_id", "document_chunks", ["embedding_id"]
    )
    op.create_index(
        "ix_chunks_document_page", "document_chunks", ["document_id", "page_number"]
    )
    op.create_index(
        "ix_chunks_document_index", "document_chunks", ["document_id", "chunk_index"]
    )

    op.create_table(
        "chat_messages",
        sa.Column("project_id", UUID, nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column(
            "role",
            sa.Enum(
                "USER", "ASSISTANT", name="messagerole", native_enum=False, length=16
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "citations",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "trace",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("id", UUID, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_project_id", "chat_messages", ["project_id"])
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index(
        "ix_chat_session_created", "chat_messages", ["session_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_chat_session_created", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_project_id", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chunks_document_index", table_name="document_chunks")
    op.drop_index("ix_chunks_document_page", table_name="document_chunks")
    op.drop_index("ix_document_chunks_embedding_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")

    op.drop_index("ix_documents_project_created", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_table("documents")
