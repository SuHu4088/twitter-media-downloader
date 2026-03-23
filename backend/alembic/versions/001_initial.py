"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(50), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table(
        'twitter_users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twitter_id', sa.String(50), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('profile_image_url', sa.String(500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('followers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('friends_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('statuses_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_following', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitter_id'),
    )
    op.create_index(op.f('ix_twitter_users_username'), 'twitter_users', ['username'], unique=False)

    op.create_table(
        'twitter_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twitter_user_id', sa.String(50), nullable=False),
        sa.Column('twitter_username', sa.String(100), nullable=False),
        sa.Column('access_token', sa.String(500), nullable=False),
        sa.Column('refresh_token', sa.String(500), nullable=True),
        sa.Column('token_expires_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitter_user_id'),
    )
    op.create_index(op.f('ix_twitter_accounts_user_id'), 'twitter_accounts', ['user_id'], unique=False)

    op.create_table(
        'tweets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twitter_id', sa.String(50), nullable=False),
        sa.Column('twitter_user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twitter_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('lang', sa.String(10), nullable=True),
        sa.Column('retweet_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('like_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('reply_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('quote_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_retweet', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_quote', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_liked_by_me', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_bookmarked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['twitter_user_id'], ['twitter_users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['twitter_account_id'], ['twitter_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('twitter_id'),
    )
    op.create_index(op.f('ix_tweets_published_at'), 'tweets', ['published_at'], unique=False)
    op.create_index(op.f('ix_tweets_twitter_user_id'), 'tweets', ['twitter_user_id'], unique=False)
    op.create_index(op.f('ix_tweets_twitter_account_id'), 'tweets', ['twitter_account_id'], unique=False)

    op.create_table(
        'download_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('twitter_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('task_type', sa.String(50), nullable=False),
        sa.Column('target_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('total_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('downloaded_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('skipped_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['twitter_account_id'], ['twitter_accounts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_user_id'], ['twitter_users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_download_tasks_user_id'), 'download_tasks', ['user_id'], unique=False)
    op.create_index(op.f('ix_download_tasks_twitter_account_id'), 'download_tasks', ['twitter_account_id'], unique=False)
    op.create_index(op.f('ix_download_tasks_task_type'), 'download_tasks', ['task_type'], unique=False)
    op.create_index(op.f('ix_download_tasks_status'), 'download_tasks', ['status'], unique=False)

    op.create_table(
        'media_files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tweet_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_type', sa.String(20), nullable=False),
        sa.Column('url', sa.String(1000), nullable=False),
        sa.Column('local_path', sa.String(500), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('download_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['tweet_id'], ['tweets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_media_files_tweet_id'), 'media_files', ['tweet_id'], unique=False)
    op.create_index(op.f('ix_media_files_file_hash'), 'media_files', ['file_hash'], unique=False)
    op.create_index(op.f('ix_media_files_download_status'), 'media_files', ['download_status'], unique=False)

    op.create_table(
        'telegram_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('media_file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chat_id', sa.String(50), nullable=False),
        sa.Column('message_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['media_file_id'], ['media_files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_telegram_uploads_media_file_id'), 'telegram_uploads', ['media_file_id'], unique=False)
    op.create_index(op.f('ix_telegram_uploads_status'), 'telegram_uploads', ['status'], unique=False)

    op.create_table(
        'system_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
    )


def downgrade() -> None:
    op.drop_table('system_configs')
    op.drop_index(op.f('ix_telegram_uploads_status'), table_name='telegram_uploads')
    op.drop_index(op.f('ix_telegram_uploads_media_file_id'), table_name='telegram_uploads')
    op.drop_table('telegram_uploads')
    op.drop_index(op.f('ix_media_files_download_status'), table_name='media_files')
    op.drop_index(op.f('ix_media_files_file_hash'), table_name='media_files')
    op.drop_index(op.f('ix_media_files_tweet_id'), table_name='media_files')
    op.drop_table('media_files')
    op.drop_index(op.f('ix_download_tasks_status'), table_name='download_tasks')
    op.drop_index(op.f('ix_download_tasks_task_type'), table_name='download_tasks')
    op.drop_index(op.f('ix_download_tasks_twitter_account_id'), table_name='download_tasks')
    op.drop_index(op.f('ix_download_tasks_user_id'), table_name='download_tasks')
    op.drop_table('download_tasks')
    op.drop_index(op.f('ix_tweets_twitter_account_id'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_twitter_user_id'), table_name='tweets')
    op.drop_index(op.f('ix_tweets_published_at'), table_name='tweets')
    op.drop_table('tweets')
    op.drop_index(op.f('ix_twitter_accounts_user_id'), table_name='twitter_accounts')
    op.drop_table('twitter_accounts')
    op.drop_index(op.f('ix_twitter_users_username'), table_name='twitter_users')
    op.drop_table('twitter_users')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
