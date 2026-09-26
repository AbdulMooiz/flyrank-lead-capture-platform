"""initial schema"""
from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("tenants", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(120), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_table("users", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_table("widgets", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("type", sa.String(30), nullable=False), sa.Column("title", sa.String(160), nullable=False), sa.Column("description", sa.Text()), sa.Column("fields", sa.JSON(), nullable=False), sa.Column("button_text", sa.String(80), nullable=False), sa.Column("display_options", sa.JSON(), nullable=False), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))
    op.create_index("ix_widgets_tenant_id", "widgets", ["tenant_id"])
    op.create_table("submissions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("tenant_id", sa.String(36), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False), sa.Column("widget_id", sa.String(36), sa.ForeignKey("widgets.id", ondelete="CASCADE"), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("ip_address", sa.String(64)), sa.Column("country", sa.String(100)), sa.Column("country_code", sa.String(8)), sa.Column("city", sa.String(120)), sa.Column("region", sa.String(120)), sa.Column("geo_provider", sa.String(30)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()), sa.Column("idempotency_key", sa.String(255)), sa.UniqueConstraint("widget_id", "idempotency_key", name="uq_submission_widget_idempotency"))
    for name, table, cols in [("ix_submissions_tenant_id", "submissions", ["tenant_id"]), ("ix_submissions_widget_id", "submissions", ["widget_id"]), ("ix_submissions_country", "submissions", ["country"]), ("ix_submissions_created_at", "submissions", ["created_at"]), ("ix_submission_tenant_created", "submissions", ["tenant_id", "created_at"])]: op.create_index(name, table, cols)
    op.create_table("side_effect_jobs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("submission_id", sa.String(36), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("status", sa.String(20), nullable=False), sa.Column("attempts", sa.Integer(), nullable=False), sa.Column("last_error", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade() -> None:
    op.drop_table("side_effect_jobs")
    op.drop_table("submissions")
    op.drop_table("widgets")
    op.drop_table("users")
    op.drop_table("tenants")
