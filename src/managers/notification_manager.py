from winotify import Notification, audio

# NotificationManager handles sending system notifications.
class NotificationManager:
    @staticmethod
    def send_notification(title, message):
        """
        Sends a system notification with the given title and message.
        """
        notification = Notification(
            app_id="File Copy Assistant",
            title=title,
            msg=message,
            duration="short"
        )
        notification.set_audio(audio.Default, loop=False)
        notification.show()
