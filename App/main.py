import json
import random
import base64
import io
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.core.window import Window
from kivy.utils import platform
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivy.network.urlrequest import UrlRequest
from kivy.graphics.texture import Texture
from functools import partial
import threading
import websocket._app as websocket_app
import os
from kivy.storage.jsonstore import JsonStore

# Setup storage for app settings
config_dir = os.path.join(os.path.expanduser('~'), '.drowningdetection')
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
settings_store = JsonStore(os.path.join(config_dir, 'settings.json'))

# Notification setup for Android
if platform == "android":
    from jnius import autoclass
    from kivy.clock import run_on_ui_thread
    
    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    NotificationManager = autoclass("android.app.NotificationManager")
    NotificationChannel = autoclass("android.app.NotificationChannel")
    NotificationCompat = autoclass("androidx.core.app.NotificationCompat")
    Context = autoclass("android.content.Context")
    Intent = autoclass("android.content.Intent")
    PendingIntent = autoclass("android.app.PendingIntent")
    String = autoclass("java.lang.String")
    Vibrator = autoclass("android.os.Vibrator")
    VibrationEffect = autoclass("android.os.VibrationEffect")
    Service = autoclass("android.app.Service")
    Build = autoclass("android.os.Build")
    
    CHANNEL_ID = "drowning_alerts"
    
    # Create a notification channel
    def create_notification_channel():
        if Build.VERSION.SDK_INT >= 26:  # Check if API level 26 or higher
            notification_manager = PythonActivity.mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
            channel = NotificationChannel(CHANNEL_ID, "Drowning Alerts", NotificationManager.IMPORTANCE_HIGH)
            channel.setDescription("Alerts when drowning is detected")
            channel.enableVibration(True)
            channel.enableLights(True)
            notification_manager.createNotificationChannel(channel)
    
    # Create intent to open app when notification is tapped
    def create_notification_intent():
        # Create an intent that will open the app
        intent = PythonActivity.mActivity.getIntent()
        intent.addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP)
        intent.putExtra("open_live_view", True)  # Flag to indicate opening live view
        
        # Create a PendingIntent with the intent
        pending_intent = PendingIntent.getActivity(
            PythonActivity.mActivity, 0, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        )
        return pending_intent
    
    def send_notification(title, text):
        notification_manager = PythonActivity.mActivity.getSystemService(Context.NOTIFICATION_SERVICE)
        
        # Create notification builder
        builder = NotificationCompat.Builder(PythonActivity.mActivity, CHANNEL_ID)
        builder.setContentTitle(title)
        builder.setContentText(text)
        builder.setSmallIcon(PythonActivity.mActivity.getApplicationInfo().icon)
        builder.setPriority(NotificationCompat.PRIORITY_HIGH)
        builder.setAutoCancel(True)
        
        # Set vibration pattern
        builder.setVibrate([300, 100, 300, 100, 300])
        
        # Set intent to open app when notification is tapped
        builder.setContentIntent(create_notification_intent())
        
        # Show notification
        notification_manager.notify(1, builder.build())
        
        # Also vibrate the device
        vibrator = PythonActivity.mActivity.getSystemService(Context.VIBRATOR_SERVICE)
        if Build.VERSION.SDK_INT >= 26:
            vibration_effect = VibrationEffect.createWaveform([300, 100, 300, 100, 300], -1)
            vibrator.vibrate(vibration_effect)
        else:
            vibrator.vibrate(1000)  # For older devices

    create_notification_channel()
else:
    # Fallback for non-Android platforms
    def send_notification(title, text):
        print(f"NOTIFICATION: {title} - {text}")

class SetupScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=15)
        
        title = MDLabel(text="Drowning Detection System", 
                      halign="center", 
                      font_style="H5",
                      size_hint_y=None, 
                      height=50)
        
        # Load the saved WebSocket URL if available
        default_url = "ws://localhost:8765"
        if settings_store.exists('websocket'):
            default_url = settings_store.get('websocket')['url']
            
        self.url_input = MDTextField(
            hint_text="WebSocket URL (e.g., ws://192.168.1.100:8765)",
            helper_text="Enter the WebSocket server address",
            helper_text_mode="on_focus",
            size_hint_y=None,
            height=80,
            text=default_url
        )
        
        self.connect_button = MDRaisedButton(
            text="Connect to Server",
            pos_hint={"center_x": 0.5},
            size_hint=(0.8, None),
            height=50,
            on_release=self.connect_to_server
        )
        
        self.test_mode_button = MDRaisedButton(
            text="Start Test Mode (No Server)",
            pos_hint={"center_x": 0.5},
            size_hint=(0.8, None),
            height=50,
            on_release=self.enable_test_mode
        )
        
        layout.add_widget(title)
        layout.add_widget(self.url_input)
        layout.add_widget(self.connect_button)
        layout.add_widget(self.test_mode_button)
        self.add_widget(layout)
    
    def connect_to_server(self, instance):
        app = MDApp.get_running_app()
        url = self.url_input.text
        
        # Save the WebSocket URL
        settings_store.put('websocket', url=url)
        
        app.websocket_url = url
        app.connect_to_websocket()

    def enable_test_mode(self, instance):
        app = MDApp.get_running_app()
        app.enable_test_mode()
        app.sm.current = "home"

class LiveViewScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=10, spacing=10)
        
        # Title label
        title_label = MDLabel(
            text="Drowning Detection System - Live View",
            halign="center",
            theme_text_color="Primary",
            font_style="H6",
            size_hint_y=None,
            height=40
        )
        
        # Image feed
        self.image_feed = Image(
            source="",
            size_hint=(1, 0.6),
            allow_stretch=True,
            keep_ratio=True
        )
        
        # Alert card
        alert_card = MDCard(
            orientation="vertical",
            padding=10,
            size_hint=(1, None),
            height=150,
            md_bg_color=[0.9, 0.2, 0.2, 0.8]  # Red background for alert
        )
        
        alert_title = MDLabel(
            text="⚠️ ALERT - PERSON DROWNING",
            halign="center",
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1],
            font_style="H6",
            bold=True
        )
        
        self.coordinates_label = MDLabel(
            text="Coordinates: None",
            halign="center",
            theme_text_color="Custom",
            text_color=[1, 1, 1, 1]
        )
        
        alert_card.add_widget(alert_title)
        alert_card.add_widget(self.coordinates_label)
        
        # Dismiss button
        self.dismiss_button = MDRaisedButton(
            text="Dismiss as False Alert",
            pos_hint={"center_x": 0.5},
            size_hint=(0.8, None),
            height=50,
            on_release=self.dismiss_alert
        )
        
        # Status label
        self.status_label = MDLabel(
            text="Status: Connected",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=30
        )
        
        # Add all widgets to layout
        layout.add_widget(title_label)
        layout.add_widget(self.image_feed)
        layout.add_widget(alert_card)
        layout.add_widget(self.dismiss_button)
        layout.add_widget(self.status_label)
        
        self.add_widget(layout)

    def update_image(self, image_data):
        # Convert base64 image to Kivy texture
        try:
            # Decode base64 image
            img_bytes = base64.b64decode(image_data)
            
            # Create a BytesIO object
            img_buffer = io.BytesIO(img_bytes)
            
            # Load the image using CoreImage
            img = CoreImage(img_buffer, ext='jpg')
            
            # Update the image texture
            self.image_feed.texture = img.texture
        except Exception as e:
            print(f"Error updating image: {e}")

    def update_coordinates(self, coordinates):
        self.coordinates_label.text = f"Coordinates: {coordinates}"

    def update_status(self, status):
        self.status_label.text = f"Status: {status}"

    def dismiss_alert(self, instance):
        app = MDApp.get_running_app()
        app.sm.current = "home"

class HomeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", padding=20, spacing=15)
        
        title = MDLabel(
            text="Drowning Detection System", 
            halign="center", 
            font_style="H5",
            size_hint_y=None, 
            height=50
        )
        
        self.status_label = MDLabel(
            text="System Running in Background", 
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=30
        )
        
        background_info = MDLabel(
            text="The app is now monitoring for drowning alerts in the background.\n"
                 "You will receive a notification if a drowning incident is detected.",
            halign="center",
            theme_text_color="Secondary",
            size_hint_y=None,
            height=100
        )
        
        setup_button = MDRaisedButton(
            text="Change WebSocket Settings",
            pos_hint={"center_x": 0.5},
            size_hint=(0.8, None),
            height=50,
            on_release=self.go_to_setup
        )
        
        layout.add_widget(title)
        layout.add_widget(self.status_label)
        layout.add_widget(background_info)
        layout.add_widget(setup_button)
        self.add_widget(layout)
    
    def go_to_setup(self, instance):
        app = MDApp.get_running_app()
        app.sm.current = "setup"
    
    def update_status(self, status):
        self.status_label.text = f"Status: {status}"

class DrowningDetectionApp(MDApp):
    def build(self):
        self.title = "Drowning Detection System"
        self.websocket_url = None
        self.ws = None
        self.ws_thread = None
        self.last_alert_data = None
        
        self.sm = ScreenManager()
        self.sm.add_widget(SetupScreen(name="setup"))
        self.sm.add_widget(HomeScreen(name="home"))
        self.sm.add_widget(LiveViewScreen(name="live_view"))
        
        # Check if we have saved WebSocket settings to auto-connect
        if settings_store.exists('websocket'):
            self.websocket_url = settings_store.get('websocket')['url']
            Clock.schedule_once(self.auto_connect, 1)
            self.sm.current = "home"
        else:
            self.sm.current = "setup"
        
        # Check if app was launched from notification
        if platform == "android":
            intent = PythonActivity.mActivity.getIntent()
            if intent.hasExtra("open_live_view"):
                Clock.schedule_once(self.show_live_view_from_notification, 1.5)
        
        return self.sm
    
    def auto_connect(self, dt):
        self.connect_to_websocket()
    
    def show_live_view_from_notification(self, dt):
        # If we have alert data, update the live view screen
        if self.last_alert_data:
            self.update_live_view_with_data(self.last_alert_data)
        
        # Switch to live view
        self.sm.current = "live_view"

    def connect_to_websocket(self):
        # Close existing connection if any
        if self.ws:
            self.ws.close()
            
        if self.ws_thread and self.ws_thread.is_alive():
            # Wait for thread to finish
            self.ws_thread.join(0.1)

        # Start WebSocket in a separate thread
        self.ws_thread = threading.Thread(target=self.websocket_thread)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Switch to home screen
        self.sm.current = "home"
        
        # Update status on home screen
        Clock.schedule_once(lambda dt: self.update_connection_status("Connecting..."))

    def websocket_thread(self):
        try:
            # Define WebSocket callbacks
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    Clock.schedule_once(partial(self.process_websocket_data, data))
                except json.JSONDecodeError:
                    print("Received invalid JSON data")
                except Exception as e:
                    print(f"Error processing message: {e}")
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
                error_str = str(error)  # Capture error as a string
                Clock.schedule_once(lambda dt, err=error_str: self.update_connection_status(f"Error: {err}"))
            
            def on_close(ws, close_status_code, close_msg):
                print(f"WebSocket closed: {close_status_code} - {close_msg}")
                Clock.schedule_once(lambda dt: self.update_connection_status("Disconnected"))
                # Try to reconnect after a delay
                Clock.schedule_once(self.reconnect, 5)
            
            def on_open(ws):
                print("WebSocket connection established")
                Clock.schedule_once(lambda dt: self.update_connection_status("Connected"))
            
            # Create and connect WebSocket
            self.ws = websocket_app.WebSocketApp(
                self.websocket_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            self.ws.run_forever()
            
        except Exception as e:
            print(f"WebSocket thread error: {e}")
            error_str = str(e)  # Capture error value
            Clock.schedule_once(lambda dt, err=error_str: self.update_connection_status(f"Error: {err}"))
            # Try to reconnect after a delay
            Clock.schedule_once(self.reconnect, 5)

    def reconnect(self, dt):
        # Only attempt to reconnect if we're not on the setup screen
        if self.sm.current != "setup" and self.websocket_url:
            print("Attempting to reconnect...")
            Clock.schedule_once(lambda dt: self.update_connection_status("Reconnecting..."))
            
            # Create a new thread for connection
            self.ws_thread = threading.Thread(target=self.websocket_thread)
            self.ws_thread.daemon = True
            self.ws_thread.start()

    def process_websocket_data(self, data, dt):
        # Check if drowning is detected
        if data.get("drowning_detected") and data.get("drowning_boxes", []):
            # Store the alert data
            self.last_alert_data = data
            
            # If the app is in foreground and not already on live view,
            # send notification and switch to live view screen
            if self.sm.current != "live_view":
                # Send notification
                send_notification("ALERT - PERSON DROWNING", "Tap to check")

                # If app is in foreground, switch to live view screen
                if not self.is_app_in_background():
                    self.update_live_view_with_data(data)
                    self.sm.current = "live_view"
        
        # Always update the live view if we're on that screen
        if self.sm.current == "live_view":
            self.update_live_view_with_data(data)
    
    def update_live_view_with_data(self, data):
        # Update image if available
        if "image" in data:
            self.sm.get_screen("live_view").update_image(data["image"])
        
        # Update coordinates if drowning is detected
        if data.get("drowning_detected") and data.get("drowning_boxes", []):
            coordinates = [
                f"X: {box.get('center_x', 0)}, Y: {box.get('center_y', 0)}" 
                for box in data["drowning_boxes"]
            ]
            coordinates_text = "; ".join(coordinates)
            self.sm.get_screen("live_view").update_coordinates(coordinates_text)

    def is_app_in_background(self):
        # On Android, we would check if the activity is in background
        # For simplicity, we'll assume it's not in background when running on desktop
        if platform == "android":
            # This is a simplification; in reality, you'd use Android APIs to determine this
            return False
        return False

    def update_connection_status(self, status):
        # Update status on all screens that have status indicators
        for screen_name in ["live_view", "home"]:
            screen = self.sm.get_screen(screen_name)
            if hasattr(screen, "update_status"):
                screen.update_status(status)

    def enable_test_mode(self, dt=None):
        """Enable test mode to simulate alerts without a WebSocket server"""
        print("Enabling test mode with simulated alerts")
        self.update_connection_status("Test Mode Active")
        
        # Generate random coordinates for testing
        def generate_alert(dt):
            test_data = {
                "drowning_detected": True,
                "drowning_boxes": [
                    {
                        "center_x": random.randint(100, 500),
                        "center_y": random.randint(100, 500)
                    }
                ],
                # Add empty image data or a test image if needed
                "image": ""  
            }
            self.process_websocket_data(test_data, 0)
        
        # Schedule random alerts
        Clock.schedule_interval(generate_alert, 15)  # Alert every 15 seconds

    def on_pause(self):
        # This is called when the app is paused/backgrounded on Android
        # Return True to allow the app to continue running in the background
        return True
    
    def on_resume(self):
        # This is called when the app is resumed from background on Android
        # Check if we should show the alert screen based on intent
        if platform == "android":
            intent = PythonActivity.mActivity.getIntent()
            if intent.hasExtra("open_live_view"):
                Clock.schedule_once(self.show_live_view_from_notification, 0.5)
                # Clear the extra after processing
                intent.removeExtra("open_live_view")

    def on_stop(self):
        # This is called when the app is fully closed
        # Close WebSocket connection
        if self.ws:
            self.ws.close()
        super().on_stop()

if __name__ == "__main__":
    DrowningDetectionApp().run()