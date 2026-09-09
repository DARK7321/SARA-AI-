"""Autonomous Proactive Engine for OmniBrain.

Runs background periodic heartbeat checks to anticipate user needs:
- Generates Daily Morning Briefing from Calendar and Inbox
- Meeting Guard: Alerts user before upcoming meetings within 30 minutes
- Inbox Triage: Detects important/urgent unread emails
- Synthesizes spoken audio alerts with Lady Voice AI Engine
"""
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.db.models import User, Connection, Notification
from packages.core.voice.tts import VoiceEngine, DEFAULT_LADY_VOICE, DEFAULT_HINGLISH_VOICE
from packages.connectors.gcal.actions import GCalActions, GCalSandbox
from packages.connectors.gmail.actions import GmailActions, GmailSandbox
from packages.connectors.google_auth import GoogleAuthManager

logger = logging.getLogger("omnibrain.worker.proactive")


class ProactiveEngine:
    """Coordinates autonomous proactive monitoring and notification generation."""

    def __init__(self, voice_engine: Optional[VoiceEngine] = None):
        self.voice_engine = voice_engine or VoiceEngine()
        self.oauth_manager = GoogleAuthManager()

    async def _get_access_token(self, session: AsyncSession, user_id: UUID) -> Optional[str]:
        """Fetch valid decrypted Google OAuth access token if connected."""
        res = await session.execute(
            select(Connection).where(
                Connection.user_id == user_id,
                Connection.provider == "google",
                Connection.status == "ONLINE",
            )
        )
        conn = res.scalar_one_or_none()
        if conn and conn.refresh_token_encrypted:
            try:
                token = await self.oauth_manager.get_valid_access_token(conn, session)
                return token
            except Exception as e:
                logger.warning(f"Failed to refresh Google token for user {user_id}: {e}")
        return None

    async def run_proactive_cycle(
        self,
        session: AsyncSession,
        user_id: UUID,
        force_briefing: bool = False,
        generate_audio: bool = True,
    ) -> List[Notification]:
        """Execute proactive scan: Morning Briefing, Meeting Reminders, and Inbox Triage."""
        new_notifications: List[Notification] = []

        # 1. Fetch User details
        user_res = await session.execute(select(User).where(User.id == user_id))
        user = user_res.scalar_one_or_none()
        if not user:
            return []

        user_name = user.name or "Sir"
        token = await self._get_access_token(session, user_id)

        # Connectors / Sandboxes
        gcal_actions = GCalActions()
        gmail_actions = GmailActions()

        now_utc = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # A. Daily Morning Briefing
        # -------------------------------------------------------------
        should_generate_briefing = force_briefing
        if not should_generate_briefing:
            # Check if briefing already sent within the last 16 hours
            cutoff = now_utc - timedelta(hours=16)
            brief_res = await session.execute(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.type == "BRIEFING",
                    Notification.created_at >= cutoff,
                )
            )
            if not brief_res.scalars().first():
                should_generate_briefing = True

        if should_generate_briefing:
            try:
                # Gather Calendar events
                events = await gcal_actions.execute_action(
                    action="calendar.list_events",
                    inputs={"max_results": 5},
                    access_token=token,
                )
                event_items = events if isinstance(events, list) else []

                # Gather Unread Emails
                messages = await gmail_actions.execute_action(
                    action="gmail.search",
                    inputs={"query": "is:unread", "max_results": 5},
                    access_token=token,
                )
                unread_items = messages if isinstance(messages, list) else []

                # Format Briefing
                events_count = len(event_items)
                unread_count = len(unread_items)

                event_summaries = []
                for e in event_items:
                    title = e.get("summary", "Untitled Event")
                    start = e.get("start", {}).get("dateTime", "Scheduled today")
                    event_summaries.append(f"• {title} ({start})")

                email_summaries = []
                for m in unread_items:
                    sender = m.get("from", "Unknown sender")
                    subject = m.get("subject", "No subject")
                    email_summaries.append(f"• {sender}: \"{subject}\"")

                events_text = "\n".join(event_summaries) if event_summaries else "• No upcoming meetings today."
                emails_text = "\n".join(email_summaries) if email_summaries else "• Inbox clean! No unread messages."

                message_body = (
                    f"Good morning, {user_name}! Here is your OmniBrain daily briefing:\n\n"
                    f"📅 **Calendar ({events_count} events)**:\n{events_text}\n\n"
                    f"📬 **Inbox ({unread_count} unread)**:\n{emails_text}"
                )

                spoken_text = (
                    f"Good morning, {user_name}! You have {events_count} events scheduled today, "
                    f"and {unread_count} unread emails in your inbox."
                )
                if event_items:
                    first_event = event_items[0].get("summary", "meeting")
                    spoken_text += f" Your first event is {first_event}."

                audio_b64 = None
                if generate_audio:
                    try:
                        audio_b64 = await self.voice_engine.synthesize_speech(
                            text=spoken_text,
                            voice=DEFAULT_LADY_VOICE,
                        )
                    except Exception as e:
                        logger.warning(f"Voice generation for briefing failed: {e}")

                briefing_notif = Notification(
                    user_id=user_id,
                    type="BRIEFING",
                    title="Daily Morning Briefing",
                    message=message_body,
                    spoken_text=spoken_text,
                    audio_base64=audio_b64,
                    status="UNREAD",
                    metadata_json={
                        "events_count": events_count,
                        "unread_count": unread_count,
                    },
                )
                session.add(briefing_notif)
                new_notifications.append(briefing_notif)
            except Exception as e:
                logger.error(f"Error generating morning briefing: {e}")

        # -------------------------------------------------------------
        # B. Meeting Reminders (Starting in next 35 minutes)
        # -------------------------------------------------------------
        try:
            events = await gcal_actions.execute_action(
                action="calendar.list_events",
                inputs={"max_results": 10},
                access_token=token,
            )
            if isinstance(events, list):
                for ev in events:
                    ev_id = ev.get("id")
                    ev_title = ev.get("summary", "Upcoming Meeting")
                    start_str = ev.get("start", {}).get("dateTime")
                    if not start_str or not ev_id:
                        continue

                    # Check if already notified for this event
                    existing = await session.execute(
                        select(Notification).where(
                            Notification.user_id == user_id,
                            Notification.type == "REMINDER",
                            Notification.metadata_json["event_id"].as_string() == str(ev_id),
                        )
                    )
                    if existing.scalars().first():
                        continue

                    # Check start time window
                    try:
                        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                        diff_minutes = (start_dt - now_utc).total_seconds() / 60.0
                        if 0 <= diff_minutes <= 35:
                            minutes_int = max(1, int(diff_minutes))
                            reminder_msg = f"Your meeting '{ev_title}' starts in {minutes_int} minutes."
                            spoken_rem = f"Reminder, {user_name}: {ev_title} starts in {minutes_int} minutes."
                            audio_rem = None
                            if generate_audio:
                                try:
                                    audio_rem = await self.voice_engine.synthesize_speech(
                                        text=spoken_rem,
                                        voice=DEFAULT_LADY_VOICE,
                                    )
                                except Exception as e:
                                    logger.warning(f"Voice generation for reminder failed: {e}")

                            notif = Notification(
                                user_id=user_id,
                                type="REMINDER",
                                title=f"Meeting in {minutes_int}m: {ev_title}",
                                message=reminder_msg,
                                spoken_text=spoken_rem,
                                audio_base64=audio_rem,
                                status="UNREAD",
                                metadata_json={"event_id": ev_id, "start_time": start_str},
                            )
                            session.add(notif)
                            new_notifications.append(notif)
                    except Exception as e:
                        logger.debug(f"Failed to parse datetime for event {ev_id}: {e}")
        except Exception as e:
            logger.error(f"Error checking meeting reminders: {e}")

        # -------------------------------------------------------------
        # C. Inbox Triage (Urgent / Important emails)
        # -------------------------------------------------------------
        try:
            unread_msgs = await gmail_actions.execute_action(
                action="gmail.search",
                inputs={"query": "is:unread", "max_results": 5},
                access_token=token,
            )
            if isinstance(unread_msgs, list):
                for msg in unread_msgs:
                    msg_id = msg.get("id")
                    subject = msg.get("subject", "")
                    sender = msg.get("from", "Unknown")

                    urgent_keywords = ["urgent", "asap", "important", "critical", "review"]
                    is_urgent = any(kw in subject.lower() for kw in urgent_keywords)

                    if is_urgent and msg_id:
                        # Check if already alerted
                        existing = await session.execute(
                            select(Notification).where(
                                Notification.user_id == user_id,
                                Notification.type == "INBOX_ALERT",
                                Notification.metadata_json["message_id"].as_string() == str(msg_id),
                            )
                        )
                        if not existing.scalars().first():
                            alert_msg = f"Important email from {sender}: '{subject}'"
                            spoken_alert = f"Attention {user_name}: You have an urgent email from {sender}."
                            audio_alert = None
                            if generate_audio:
                                try:
                                    audio_alert = await self.voice_engine.synthesize_speech(
                                        text=spoken_alert,
                                        voice=DEFAULT_LADY_VOICE,
                                    )
                                except Exception:
                                    pass

                            notif = Notification(
                                user_id=user_id,
                                type="INBOX_ALERT",
                                title=f"Urgent Email: {subject[:40]}",
                                message=alert_msg,
                                spoken_text=spoken_alert,
                                audio_base64=audio_alert,
                                status="UNREAD",
                                metadata_json={"message_id": msg_id, "sender": sender},
                            )
                            session.add(notif)
                            new_notifications.append(notif)
        except Exception as e:
            logger.error(f"Error performing inbox triage: {e}")

        await session.flush()
        return new_notifications
