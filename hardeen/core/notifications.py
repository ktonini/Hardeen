import os
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

class NotificationPriority(Enum):
    LOWEST = -2
    LOW = -1
    NORMAL = 0
    HIGH = 1
    EMERGENCY = 2

@dataclass
class NotificationSettings:
    """Settings for notification system"""
    enabled: bool = False
    interval: int = 10
    api_token: str = ""
    user_key: str = ""
    device: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    sound: Optional[str] = None
    retry: Optional[int] = None
    expire: Optional[int] = None
    callback: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotificationSettings':
        """Create settings from a dictionary"""
        # Handle notification interval conversion safely
        try:
            interval_str = data.get('notification_interval', "10")
            interval = int(interval_str) if interval_str.strip() else 10
        except (ValueError, TypeError):
            interval = 10

        # Handle priority conversion safely
        try:
            priority_value = int(data.get('pushover_priority', "0"))
        except (ValueError, TypeError):
            priority_value = 0

        return cls(
            enabled=data.get('notifications_enabled', False),
            interval=interval,
            api_token=data.get('pushover_api_key', ''),
            user_key=data.get('pushover_user_key', ''),
            device=data.get('pushover_device'),
            priority=NotificationPriority(priority_value),
            sound=data.get('pushover_sound')
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to a dictionary"""
        return {
            'notifications_enabled': self.enabled,
            'notification_interval': str(self.interval),
            'pushover_api_key': self.api_token,
            'pushover_user_key': self.user_key,
            'pushover_device': self.device,
            'pushover_priority': str(self.priority.value),
            'pushover_sound': self.sound
        }

@dataclass
class NotificationConfig:
    """Configuration for Pushover notifications"""
    api_token: str
    user_key: str
    device: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    sound: Optional[str] = None
    retry: Optional[int] = None
    expire: Optional[int] = None
    callback: Optional[str] = None

class NotificationManager:
    """Manages Pushover notifications"""

    PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

    def __init__(self, config: NotificationConfig):
        self.config = config

    def _convert_exr_to_png(self, exr_path: str) -> Optional[str]:
        """Convert EXR file to PNG for notification attachment"""
        try:
            import OpenImageIO as oiio
            import tempfile

            # Create a temporary file for the PNG
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
                temp_path = tmp.name

            # Read the EXR file
            buf = oiio.ImageBuf(exr_path)
            error_msg = buf.geterror()
            if error_msg:
                print(f"OpenImageIO error: {error_msg}")
                return None

            # Convert to sRGB for display
            display_buf = oiio.ImageBufAlgo.colorconvert(buf, "linear", "srgb")
            display_buf.write(temp_path)
            return temp_path

        except Exception as e:
            print(f"Error converting EXR to PNG: {str(e)}")
            return None

    def _prepare_image_attachment(self, image_path: Optional[str]) -> Optional[Dict[str, Any]]:
        """Prepare image attachment for notification"""
        if not image_path or not os.path.exists(image_path):
            return None

        try:
            # Convert EXR to PNG if needed
            if image_path.lower().endswith('.exr'):
                png_path = self._convert_exr_to_png(image_path)
                if not png_path:
                    return None
                image_path = png_path

            # Return attachment configuration
            return {
                "attachment": ("render.png", open(image_path, "rb"), "image/png")
            }

        except Exception as e:
            print(f"Error preparing image attachment: {str(e)}")
            return None

    def send_push_notification(self, message: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a push notification with optional image attachment.
        This is a convenience method that wraps send_notification with common defaults.

        Args:
            message: The notification message
            image_path: Optional path to an image file to attach

        Returns:
            Dict containing the API response
        """
        return self.send_notification(
            title="Houdini Render Update",
            message=message,
            image_path=image_path
        )

    def send_notification(
        self,
        title: str,
        message: str,
        priority: Optional[NotificationPriority] = None,
        sound: Optional[str] = None,
        url: Optional[str] = None,
        url_title: Optional[str] = None,
        timestamp: Optional[int] = None,
        image_path: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Send a notification through Pushover

        Args:
            title: Notification title
            message: Notification message
            priority: Override default priority
            sound: Override default sound
            url: URL to include in notification
            url_title: Title for the URL
            timestamp: Unix timestamp for the notification
            image_path: Path to image file to attach
            **kwargs: Additional parameters to pass to Pushover API

        Returns:
            Dict containing the API response
        """
        if not self.config.api_token or not self.config.user_key:
            return {"status": 0, "error": "Missing API token or user key"}

        data = {
            "token": self.config.api_token,
            "user": self.config.user_key,
            "title": title,
            "message": message,
            "priority": (priority or self.config.priority).value,
        }

        # Add optional parameters if provided
        if self.config.device:
            data["device"] = self.config.device
        if sound or self.config.sound:
            data["sound"] = sound or self.config.sound
        if url:
            data["url"] = url
        if url_title:
            data["url_title"] = url_title
        if timestamp:
            data["timestamp"] = timestamp

        # Add emergency priority parameters if needed
        if data["priority"] == NotificationPriority.EMERGENCY.value:
            if self.config.retry:
                data["retry"] = self.config.retry
            if self.config.expire:
                data["expire"] = self.config.expire
            if self.config.callback:
                data["callback"] = self.config.callback

        # Add any additional parameters
        data.update(kwargs)

        try:
            # Prepare image attachment if provided
            files = self._prepare_image_attachment(image_path) if image_path else {}

            # Send notification
            response = requests.post(self.PUSHOVER_API_URL, data=data, files=files)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            print(f"Error sending notification: {error_msg}")
            return {"status": 0, "error": error_msg}
        except Exception as e:
            error_msg = str(e)
            print(f"Unexpected error sending notification: {error_msg}")
            return {"status": 0, "error": error_msg}
        finally:
            # Clean up any temporary files
            if image_path and image_path.endswith('.png') and os.path.exists(image_path):
                try:
                    os.unlink(image_path)
                except Exception as e:
                    print(f"Error cleaning up temporary file: {str(e)}")

    @classmethod
    def from_environment(cls) -> Optional['NotificationManager']:
        """
        Create a NotificationManager instance from environment variables

        Environment variables:
            PUSHOVER_API_TOKEN: Your Pushover API token
            PUSHOVER_USER_KEY: Your Pushover user key
            PUSHOVER_DEVICE (optional): Device to send to
            PUSHOVER_PRIORITY (optional): Priority level (-2 to 2)
            PUSHOVER_SOUND (optional): Sound to play
        """
        api_token = os.getenv("PUSHOVER_API_TOKEN")
        user_key = os.getenv("PUSHOVER_USER_KEY")

        if not api_token or not user_key:
            return None

        config = NotificationConfig(
            api_token=api_token,
            user_key=user_key,
            device=os.getenv("PUSHOVER_DEVICE"),
            priority=NotificationPriority(int(os.getenv("PUSHOVER_PRIORITY", "0"))),
            sound=os.getenv("PUSHOVER_SOUND")
        )

        return cls(config)
