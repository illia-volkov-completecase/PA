"""initial

Revision ID: c766ff809a40
Revises:
Create Date: 2022-01-08 22:05:19.954319

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c766ff809a40'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # accounts
    op.create_table(
        'merchant',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(128)),
        sa.Column('password', sa.String(128)),
    )
    op.create_table(
        'staff',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('username', sa.String(128)),
        sa.Column('password', sa.String(128)),
    )

    # wallets
    op.create_table(
        'currency',
        sa.UniqueConstraint('code', name='uniq_currency'),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('code', sa.Enum('usd', 'uah', 'eur', 'gbp', name='currencycode'))
    )
    op.create_table(
        'wallet',
        sa.UniqueConstraint('merchant_id', 'currency_id', name='uniq_wallet'),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=3), default=sa.ColumnDefault(0)),
        sa.Column('merchant_id', sa.Integer, sa.ForeignKey('merchant.id'), nullable=False),
        sa.Column('currency_id', sa.Integer, sa.ForeignKey('currency.id'), nullable=False)
    )
    op.create_table(
        'conversion_rate',
        sa.UniqueConstraint('from_currency_id', 'to_currency_id', name='uniq_conv_rate'),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('rate', sa.Numeric(precision=20, scale=3), nullable=False),
        sa.Column('allow_reversed', sa.Boolean, nullable=False),
        sa.Column('from_currency_id', sa.Integer, sa.ForeignKey('currency.id'), nullable=False),
        sa.Column('to_currency_id', sa.Integer, sa.ForeignKey('currency.id'), nullable=False)
    )

    # transactions
    op.create_table(
        'invoice',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('token', sa.String(36), index=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=3), nullable=False),
        sa.Column('status', sa.Enum('pending', 'incomplete', 'complete', name='invoicestatus')),
        sa.Column('to_wallet_id', sa.Integer, sa.ForeignKey('wallet.id'), nullable=False),
    )
    op.create_table(
        'payment_system',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('system_type', sa.Enum('visa', name='paymentsystemtype')),
        sa.Column('decryption_key', sa.String(1024), nullable=False)
    )
    op.create_table(
        'transaction',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('transaction_type', sa.Enum('external', 'internal', name='transactiontype')),
        sa.Column('token', sa.String(36), index=True),
        sa.Column('amount', sa.Numeric(precision=20, scale=3), nullable=False),
        sa.Column('effective_amount', sa.Numeric(precision=20, scale=3), nullable=False),
        sa.Column('status',
                  sa.Enum('pending', 'success', 'fail', 'refunded', name='transactionstatus')),
        sa.Column('invoice_id', sa.Integer, sa.ForeignKey('invoice.id'), nullable=False),
        sa.Column('from_wallet_id', sa.Integer, sa.ForeignKey('wallet.id'), nullable=True)
    )
    op.create_table(
        'attempt',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('token', sa.String(36), index=True),
        sa.Column('response', sa.Text, nullable=False, default=''),
        sa.Column('status', sa.Enum('pending', 'success', 'fail', name='attemptstatus')),
        sa.Column('transaction_id', sa.Integer, sa.ForeignKey('transaction.id'), nullable=False),
        sa.Column('payment_system_id', sa.Integer, sa.ForeignKey('payment_system.id'), nullable=False)
    )


def downgrade():
    # transaction
    op.drop_table('attempt')
    op.drop_table('transaction')
    op.drop_table('payment_system')
    op.drop_table('invoice')
    op.execute('DROP TYPE invoicestatus')
    op.execute('DROP TYPE paymentsystemtype')
    op.execute('DROP TYPE transactionstatus')
    op.execute('DROP TYPE attemptstatus')

    # wallets
    op.drop_table('conversion_rate')
    op.drop_table('wallet')
    op.drop_table('currency')
    op.execute('DROP TYPE currencycode')

    # accounts
    op.drop_table('merchant')
    op.drop_table('staff')
