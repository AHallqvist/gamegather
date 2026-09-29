from src.database import get_connection

# This file is the notification layer.
# It should NOT send emails or Discord messages directly from the game logic.
# Instead, the game logic creates an event and this layer records it.
#
# In the design, the app should be structured like this:
#   game logic -> notification queue -> delivery processor
#
# For this project, we keep it simple:
#   game logic calls queue_notification(...)
#   this function writes a pending notification row
#   later, a background job or service can send the message
#
# Pseudocode:
#   when a game reaches the minimum threshold:
#       queue notification for all interested people
#   when a gathering starts:
#       queue notification for active people
#   later:
#       read queued notifications
#       send them using each person's configured method


def queue_notification(game_id: int, person_id: int, event_type: str) -> None:
    """
    Record a notification that should be sent later.

    This keeps the core app logic independent from delivery details.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (game_id, person_id, event_type, status) VALUES (?, ?, ?, 'queued')",
            (game_id, person_id, event_type),
        )
        conn.commit()


def process_notifications() -> int:
    """
    Simulate processing queued notifications.

    A real app would send with the person's configured notification method here.
    For a class project, this can be a simplified version that marks them as sent.

    Pseudocode:
        notifications = query rows where status = 'queued'
        for each notification:
            read person notification settings
            send via that method
            mark as sent
        return how many were processed
    """
    with get_connection() as conn:
        pending = conn.execute(
            """
            SELECT n.*, p.notification_method, p.notification_target
            FROM notifications n
            JOIN people p ON p.id = n.person_id
            WHERE n.status = 'queued'
            """
        ).fetchall()

        for item in pending:
            conn.execute(
                "UPDATE notifications SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = ?",
                (item["id"],),
            )
        conn.commit()

        return len(pending)
