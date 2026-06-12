import logging
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.api.deps import get_current_user
from app.models.schemas import User, WebhookSubscription, WebhookSubscriptionCreate, WebhookDeliveryLog

logger = logging.getLogger("AgentForge.WebhooksAPI")
router = APIRouter()

@router.post("/subscriptions", response_model=WebhookSubscription, status_code=status.HTTP_201_CREATED)
def create_subscription(
    *,
    session: Session = Depends(get_session),
    subscription_in: WebhookSubscriptionCreate,
    current_user: User = Depends(get_current_user)
):
    """Register a new webhook callback subscription URL."""
    db_sub = WebhookSubscription(
        target_url=subscription_in.target_url,
        event_type=subscription_in.event_type,
        secret_token=subscription_in.secret_token
    )
    session.add(db_sub)
    session.commit()
    session.refresh(db_sub)
    return db_sub

@router.get("/subscriptions", response_model=List[WebhookSubscription])
def list_subscriptions(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve all registered webhook subscriptions."""
    statement = select(WebhookSubscription)
    return session.exec(statement).all()

@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    *,
    session: Session = Depends(get_session),
    subscription_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """De-register a webhook callback subscription."""
    sub = session.get(WebhookSubscription, subscription_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    
    # Delete delivery logs associated
    stmt = select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription_id)
    logs = session.exec(stmt).all()
    for l in logs:
        session.delete(l)

    session.delete(sub)
    session.commit()
    return None

@router.get("/subscriptions/{subscription_id}/deliveries", response_model=List[WebhookDeliveryLog])
def list_delivery_logs(
    subscription_id: UUID,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    """Retrieve delivery history logs for a specific subscription."""
    statement = select(WebhookDeliveryLog).where(WebhookDeliveryLog.subscription_id == subscription_id).order_by(WebhookDeliveryLog.created_at.desc())
    return session.exec(statement).all()
