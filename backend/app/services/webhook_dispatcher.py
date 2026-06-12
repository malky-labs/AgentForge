import hmac
import hashlib
import json
import logging
import asyncio
from datetime import datetime
import httpx
from sqlmodel import Session, select
from app.core.database import engine
from app.models.schemas import WebhookSubscription, WebhookDeliveryLog

logger = logging.getLogger("AgentForge.WebhookDispatcher")

class WebhookDispatcher:
    def __init__(self):
        self.timeout = httpx.Timeout(10.0)

    def dispatch(self, event_type: str, payload: dict):
        """Asynchronously trigger webhooks matching the event_type in the background."""
        asyncio.create_task(self._async_dispatch(event_type, payload))

    async def _async_dispatch(self, event_type: str, payload: dict):
        with Session(engine) as session:
            # Query active subscriptions
            statement = select(WebhookSubscription).where(
                WebhookSubscription.is_active == True
            )
            subscriptions = session.exec(statement).all()
            
            # Filter subscriptions
            targets = [
                sub for sub in subscriptions 
                if sub.event_type == "*" or sub.event_type == event_type
            ]
            
            if not targets:
                return

            event_data = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": payload
            }
            payload_str = json.dumps(event_data)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                for sub in targets:
                    # Log delivery start
                    log_entry = WebhookDeliveryLog(
                        subscription_id=sub.id,
                        event_type=event_type,
                        payload=payload_str,
                        created_at=datetime.utcnow()
                    )
                    session.add(log_entry)
                    session.commit()
                    session.refresh(log_entry)

                    headers = {"Content-Type": "application/json"}
                    if sub.secret_token:
                        # Sign payload using HMAC SHA256
                        signature = hmac.new(
                            sub.secret_token.encode("utf-8"),
                            payload_str.encode("utf-8"),
                            hashlib.sha256
                        ).hexdigest()
                        headers["X-AgentForge-Signature"] = signature

                    try:
                        logger.info(f"Posting webhook {event_type} event to: {sub.target_url}")
                        response = await client.post(
                            sub.target_url,
                            content=payload_str,
                            headers=headers
                        )
                        log_entry.response_status = response.status_code
                        log_entry.response_body = response.text[:2000] # Cap log length
                    except Exception as err:
                        logger.error(f"Failed to post webhook event to {sub.target_url}: {err}")
                        log_entry.response_status = 0
                        log_entry.response_body = f"Delivery Error: {str(err)}"

                    session.add(log_entry)
                    session.commit()

webhook_dispatcher = WebhookDispatcher()
