from src.database import get_connection

# This file is the notification layer.
# It should NOT send emails or Discord messages directly from the game logic.
# Instead, the game logic creates an event and this layer records it.
#
# In the design, the app should be structured like this:
#   game logic -> event bus -> notification manager -> provider
#
# For this project, we keep it simple:
#   game logic calls queue_notification(...)
#   this function writes a pending notification row
#   later, a background job or service can send the message
#
# Pseudocode:
#   when a game reaches the minimum threshold:
#       queue notification for all players
#   when a gathering starts:
#       queue notification for active players
#   later:
#       read queued notifications
#       send them to the chosen provider


def queue_notification(game_id: int, player_id: int, event_type: str, provider: str) -> None:
    """
    Record a notification that should be sent later.

    This keeps the core app logic independent from provider details.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO notifications (game_id, player_id, event_type, provider, status) VALUES (?, ?, ?, ?, 'queued')",
            (game_id, player_id, event_type, provider),
        )
        conn.commit()


def process_notifications() -> int:
    """
    Simulate processing queued notifications.

    A real app would call a provider such as email or Discord here.
    For a class project, this can be a simplified version that marks them as sent.

    Pseudocode:
        notifications = query rows where status = 'queued'
        for each notification:
            send via service provider
            mark as sent
        return how many were processed
    """
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
