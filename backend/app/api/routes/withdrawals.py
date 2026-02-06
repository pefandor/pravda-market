"""
Withdrawal Routes

Endpoints for TON withdrawal requests
"""

from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.db.models import User, LedgerEntry, WithdrawalRequest
from app.api.deps import get_current_user
from app.ton.config import ton_settings
from app.core.rate_limit import limiter
from app.core.logging_config import get_logger

logger = get_logger()
router = APIRouter(prefix="/withdrawals", tags=["withdrawals"])


# --- Request/Response Models ---

class CreateWithdrawalRequest(BaseModel):
    """Request to create a withdrawal"""
    ton_address: str = Field(..., min_length=48, max_length=68, description="TON wallet address")
    amount_ton: float = Field(..., gt=0, description="Amount to withdraw in TON")


class WithdrawalResponse(BaseModel):
    """Withdrawal request response"""
    id: int
    ton_address: str
    amount_ton: float
    status: str
    tx_hash: Optional[str]
    created_at: str
    processed_at: Optional[str]
    estimated_time: Optional[str]


class WithdrawalListResponse(BaseModel):
    """List of withdrawal requests"""
    withdrawals: List[WithdrawalResponse]
    total: int


# --- Helper Functions ---

def get_user_balance_kopecks(db: Session, user_id: int) -> int:
    """Get user's available balance in kopecks"""
    return db.query(func.sum(LedgerEntry.amount_kopecks)).filter(
        LedgerEntry.user_id == user_id
    ).scalar() or 0


def get_daily_withdrawal_total(db: Session, user_id: int) -> int:
    """Get user's total withdrawals in the last 24 hours (in nanoTON)"""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)

    total = db.query(func.sum(WithdrawalRequest.amount_nanoton)).filter(
        WithdrawalRequest.user_id == user_id,
        WithdrawalRequest.status.in_(['pending', 'processing', 'completed']),
        WithdrawalRequest.created_at >= yesterday
    ).scalar()

    return total or 0


def ton_to_nanoton(ton: float) -> int:
    """Convert TON to nanoTON"""
    return int(ton * 1_000_000_000)


def nanoton_to_ton(nanoton: int) -> float:
    """Convert nanoTON to TON"""
    return nanoton / 1_000_000_000


def ton_to_kopecks(ton: float) -> int:
    """Convert TON to kopecks using current rate"""
    return int(ton * ton_settings.TON_TO_KOPECKS_RATE)


# --- Endpoints ---

@router.post("", response_model=WithdrawalResponse)
@limiter.limit("10/minute")
async def create_withdrawal(
    request: Request,
    body: CreateWithdrawalRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WithdrawalResponse:
    """
    Create a withdrawal request

    Validates:
    - Minimum withdrawal amount
    - Sufficient balance (including fee)
    - Daily withdrawal limit
    - Valid TON address format

    Creates:
    - LedgerEntry for pending withdrawal (negative)
    - WithdrawalRequest record

    Returns:
        Withdrawal request details with estimated processing time
    """
    request.state.user = user

    amount_nanoton = ton_to_nanoton(body.amount_ton)
    fee_nanoton = ton_settings.WITHDRAWAL_FEE_NANOTON
    total_nanoton = amount_nanoton + fee_nanoton

    # Validate minimum amount
    if amount_nanoton < ton_settings.MIN_WITHDRAWAL_NANOTON:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum withdrawal is {ton_settings.MIN_WITHDRAWAL_TON} TON"
        )

    # Check daily limit
    daily_total = get_daily_withdrawal_total(db, user.id)
    if daily_total + amount_nanoton > ton_settings.MAX_WITHDRAWAL_PER_DAY_NANOTON:
        remaining = nanoton_to_ton(ton_settings.MAX_WITHDRAWAL_PER_DAY_NANOTON - daily_total)
        raise HTTPException(
            status_code=400,
            detail=f"Daily withdrawal limit exceeded. Remaining: {remaining:.2f} TON"
        )

    # Convert to kopecks for balance check
    total_kopecks = ton_to_kopecks(nanoton_to_ton(total_nanoton))
    balance_kopecks = get_user_balance_kopecks(db, user.id)

    if balance_kopecks < total_kopecks:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Required: {total_kopecks/100:.2f}₽ (including {ton_settings.WITHDRAWAL_FEE_TON} TON fee)"
        )

    # Validate TON address format (basic check)
    if not (body.ton_address.startswith('EQ') or body.ton_address.startswith('UQ') or
            body.ton_address.startswith('kQ') or body.ton_address.startswith('0:')):
        raise HTTPException(
            status_code=400,
            detail="Invalid TON address format"
        )

    # Create ledger entry for pending withdrawal (lock funds)
    ledger_entry = LedgerEntry(
        user_id=user.id,
        amount_kopecks=-total_kopecks,  # Negative = deduction
        type='withdrawal_pending',
        reference_id=None  # Will update after creating withdrawal request
    )
    db.add(ledger_entry)
    db.flush()  # Get ledger_entry.id

    # Create withdrawal request
    withdrawal = WithdrawalRequest(
        user_id=user.id,
        ton_address=body.ton_address,
        amount_nanoton=amount_nanoton,
        status='pending',
        ledger_entry_id=ledger_entry.id
    )
    db.add(withdrawal)
    db.flush()

    # Update ledger entry with reference
    ledger_entry.reference_id = withdrawal.id
    db.commit()
    db.refresh(withdrawal)

    logger.info(
        "Withdrawal request created",
        extra={
            "user_id": user.id,
            "withdrawal_id": withdrawal.id,
            "amount_ton": body.amount_ton,
            "ton_address": body.ton_address[:20] + "..."
        }
    )

    return WithdrawalResponse(
        id=withdrawal.id,
        ton_address=withdrawal.ton_address,
        amount_ton=nanoton_to_ton(withdrawal.amount_nanoton),
        status=withdrawal.status,
        tx_hash=withdrawal.tx_hash,
        created_at=withdrawal.created_at.isoformat(),
        processed_at=withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
        estimated_time="30 минут"
    )


@router.get("", response_model=WithdrawalListResponse)
@limiter.limit("60/minute")
async def list_withdrawals(
    request: Request,
    limit: int = 20,
    offset: int = 0,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WithdrawalListResponse:
    """
    List user's withdrawal requests

    Query params:
        - limit: max results (default 20, max 100)
        - offset: pagination offset
        - status: filter by status (pending, processing, completed, failed, cancelled)

    Returns:
        List of withdrawal requests with total count
    """
    request.state.user = user

    # Validate pagination
    limit = min(max(limit, 1), 100)

    # Build query
    query = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.user_id == user.id
    )

    if status:
        if status not in ['pending', 'processing', 'completed', 'failed', 'cancelled']:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        query = query.filter(WithdrawalRequest.status == status)

    # Get total count
    total = query.count()

    # Get paginated results
    withdrawals = query.order_by(
        WithdrawalRequest.created_at.desc()
    ).limit(limit).offset(offset).all()

    return WithdrawalListResponse(
        withdrawals=[
            WithdrawalResponse(
                id=w.id,
                ton_address=w.ton_address,
                amount_ton=nanoton_to_ton(w.amount_nanoton),
                status=w.status,
                tx_hash=w.tx_hash,
                created_at=w.created_at.isoformat(),
                processed_at=w.processed_at.isoformat() if w.processed_at else None,
                estimated_time="30 минут" if w.status == 'pending' else None
            )
            for w in withdrawals
        ],
        total=total
    )


@router.get("/{withdrawal_id}", response_model=WithdrawalResponse)
@limiter.limit("60/minute")
async def get_withdrawal(
    request: Request,
    withdrawal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> WithdrawalResponse:
    """
    Get a specific withdrawal request

    Args:
        withdrawal_id: ID of the withdrawal request

    Returns:
        Withdrawal request details

    Raises:
        404: Withdrawal not found or doesn't belong to user
    """
    request.state.user = user

    withdrawal = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.id == withdrawal_id,
        WithdrawalRequest.user_id == user.id
    ).first()

    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")

    return WithdrawalResponse(
        id=withdrawal.id,
        ton_address=withdrawal.ton_address,
        amount_ton=nanoton_to_ton(withdrawal.amount_nanoton),
        status=withdrawal.status,
        tx_hash=withdrawal.tx_hash,
        created_at=withdrawal.created_at.isoformat(),
        processed_at=withdrawal.processed_at.isoformat() if withdrawal.processed_at else None,
        estimated_time="30 минут" if withdrawal.status == 'pending' else None
    )


@router.delete("/{withdrawal_id}")
@limiter.limit("10/minute")
async def cancel_withdrawal(
    request: Request,
    withdrawal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cancel a pending withdrawal request

    Only pending withdrawals can be cancelled.
    Refunds the locked amount back to user's balance.

    Args:
        withdrawal_id: ID of the withdrawal request

    Returns:
        Success message

    Raises:
        404: Withdrawal not found
        400: Withdrawal cannot be cancelled (not pending)
    """
    request.state.user = user

    withdrawal = db.query(WithdrawalRequest).filter(
        WithdrawalRequest.id == withdrawal_id,
        WithdrawalRequest.user_id == user.id
    ).first()

    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal request not found")

    if withdrawal.status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel withdrawal in '{withdrawal.status}' status"
        )

    # Get the original ledger entry amount
    original_entry = db.query(LedgerEntry).filter(
        LedgerEntry.id == withdrawal.ledger_entry_id
    ).first()

    if original_entry:
        # Create refund ledger entry
        refund_entry = LedgerEntry(
            user_id=user.id,
            amount_kopecks=-original_entry.amount_kopecks,  # Positive (refund)
            type='withdrawal_cancelled',
            reference_id=withdrawal.id
        )
        db.add(refund_entry)

    # Update withdrawal status
    withdrawal.status = 'cancelled'
    withdrawal.processed_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(
        "Withdrawal cancelled",
        extra={
            "user_id": user.id,
            "withdrawal_id": withdrawal.id
        }
    )

    return {"message": "Withdrawal cancelled successfully", "id": withdrawal_id}
