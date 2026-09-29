from src.database import get_connection


def queue_notification(
    game_id: int,
    recipient_role: str,
    recipient_name: str,
    notification_method: str,
    notification_target: str,
    event_type: str,
) -> None:
    """Record a notification that should be sent later."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO notifications (
                game_id,
                recipient_role,
                recipient_name,
                notification_method,
                notification_target,
                event_type,
                status
            ) VALUES (?, ?, ?, ?, ?, ?, 'queued')
            """,
            (
                game_id,
                recipient_role,
                recipient_name,
                notification_method,
                notification_target,
                event_type,
            ),
        )
        conn.commit()


def process_notifications() -> int:
    """Simulate processing queued notifications by marking them as sent."""
    with get_connection() as conn:
        pending = conn.execute(
            "SELECT * FROM notifications WHERE status = 'queued'"
        ).fetchall()

        for item in pending:
            conn.execute(
                "UPDATE notifications SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (item["id"],),
            )
        conn.commit()

        return len(pending)
