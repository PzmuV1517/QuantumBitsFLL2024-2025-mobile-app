import os
import io
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle
from kivy.utils import get_color_from_hex
from kivy.properties import BooleanProperty
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.animation import Animation

import websocket
import threading
import base64
from PIL import Image as PILImage

# Define colors to match web version from client.html
PRIMARY_COLOR = "#2c3e50"
SECONDARY_COLOR = "#3498db"
ALERT_COLOR = "#e74c3c"
BACKGROUND_COLOR = "#ecf0f1"
TEXT_COLOR = "#2c3e50"
CARD_BACKGROUND = "#ffffff"
SUCCESS_COLOR = "#2ecc71"

class StatusIndicator(BoxLayout):
    def __init__(self, **kwargs):
        super(StatusIndicator, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(30)
        self.padding = [dp(10), 0]
        self.spacing = dp(8)
        
        self.status_dot = BoxLayout()
        self.status_dot.size_hint = (None, None)
        self.status_dot.size = (dp(12), dp(12))
        
        with self.status_dot.canvas:
            Color(*get_color_from_hex(SUCCESS_COLOR))
            self.dot = Rectangle(pos=self.status_dot.pos, size=self.status_dot.size)
        
        self.status_text = Label(
            text="System Active - Monitoring Pool",
            color=get_color_from_hex("#7f8c8d"),
            font_size=dp(14),
            size_hint_x=1,
            halign='left',
            valign='middle'
        )
        self.status_text.bind(size=self.status_text.setter('text_size'))
        
        self.add_widget(self.status_dot)
        self.add_widget(self.status_text)
        
        self.bind(pos=self._update_canvas, size=self._update_canvas)
    
    def _update_canvas(self, *args):
        self.status_dot.pos = self.pos
        self.dot.pos = self.status_dot.pos
    
    def update_status(self, connected=True, text=None):
        self.status_dot.canvas.clear()
        with self.status_dot.canvas:
            if connected:
                Color(*get_color_from_hex(SUCCESS_COLOR))
            else:
                Color(*get_color_from_hex(ALERT_COLOR))
            self.dot = Rectangle(pos=self.status_dot.pos, size=self.status_dot.size)
        
        if text:
            self.status_text.text = text


class AlertMessage(BoxLayout):
    visible = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super(AlertMessage, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.size_hint_y = None
        self.height = dp(60)
        self.padding = [dp(10), dp(5)]
        
        with self.canvas.before:
            Color(*get_color_from_hex(ALERT_COLOR))
            self.rect = Rectangle(pos=self.pos, size=self.size)
        
        self.message = Label(
            text="⚠️ DROWNING DETECTED - IMMEDIATE ACTION REQUIRED",
            color=(1, 1, 1, 1),
            font_size=dp(16),
            bold=True,
            halign='center',
            valign='middle'
        )
        self.message.bind(size=self.message.setter('text_size'))
        
        self.add_widget(self.message)
        self.bind(pos=self.update_rect, size=self.update_rect)
        self.opacity = 0  # Start hidden
        
    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size
    
    def show(self):
        if not self.visible:
            self.visible = True
            self.opacity = 1
            self.start_pulse_animation()
            # Try to vibrate the phone
            try:
                from jnius import autoclass
                vibrator = autoclass('android.os.Vibrator')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                vibrator = activity.getSystemService(activity.VIBRATOR_SERVICE)
                vibrator.vibrate([0, 300, 100, 300, 100, 300], -1)  # Vibrate in a pattern
            except Exception as e:
                print(f"Could not vibrate: {e}")
    
    def hide(self):
        if self.visible:
            self.visible = False
            self.opacity = 0
            self.stop_pulse_animation()
            # Stop vibration if possible
            try:
                from jnius import autoclass
                vibrator = autoclass('android.os.Vibrator')
                activity = autoclass('org.kivy.android.PythonActivity').mActivity
                vibrator = activity.getSystemService(activity.VIBRATOR_SERVICE)
                vibrator.cancel()
            except:
                pass
    
    def start_pulse_animation(self):
        anim = Animation(opacity=0.8, duration=0.75) + Animation(opacity=1, duration=0.75)
        anim.repeat = True
        anim.start(self)
    
    def stop_pulse_animation(self):
        Animation.cancel_all(self)


class DetectionInfo(BoxLayout):
    def __init__(self, **kwargs):
        super(DetectionInfo, self).__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = [dp(10), dp(5)]
        self.spacing = dp(10)
        
        self.no_detection_label = Label(
            text="No drowning incidents detected.",
            color=get_color_from_hex("#7f8c8d"),
            font_size=dp(14),
            italic=True,
            halign='center',
            valign='middle'
        )
        self.no_detection_label.bind(size=self.no_detection_label.setter('text_size'))
        
        self.add_widget(self.no_detection_label)
    
    def update_detections(self, drowning_boxes=None):
        self.clear_widgets()
        
        if not drowning_boxes or len(drowning_boxes) == 0:
            self.add_widget(self.no_detection_label)
            return
            
        for i, box in enumerate(drowning_boxes):
            detection_item = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(80),
                padding=[dp(8), dp(5)]
            )
            
            with detection_item.canvas.before:
                Color(*get_color_from_hex("#EBF5FB"))  # Light blue background
                Rectangle(pos=detection_item.pos, size=detection_item.size)
                
                # Left border
                Color(*get_color_from_hex(SECONDARY_COLOR))
                Rectangle(
                    pos=detection_item.pos,
                    size=(dp(4), detection_item.height)
                )
            
            detection_label = Label(
                text=f"Drowning Person #{i+1} Detected",
                color=get_color_from_hex(TEXT_COLOR),
                font_size=dp(14),
                size_hint_y=None,
                height=dp(20),
                halign='left'
            )
            detection_label.bind(size=detection_label.setter('text_size'))
            
            coordinates = GridLayout(
                cols=2,
                spacing=[dp(5), dp(5)],
                size_hint_y=None,
                height=dp(40)
            )
            
            center_x = box.get('center_x', 0)
            center_y = box.get('center_y', 0)
            
            x_coord = Label(
                text=f"X: {center_x}",
                color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(30),
                halign='center',
                valign='middle'
            )
            
            y_coord = Label(
                text=f"Y: {center_y}",
                color=(1, 1, 1, 1),
                size_hint_y=None,
                height=dp(30),
                halign='center',
                valign='middle'
            )
            
            with x_coord.canvas.before:
                Color(*get_color_from_hex(SECONDARY_COLOR))
                Rectangle(pos=x_coord.pos, size=x_coord.size)
                
            with y_coord.canvas.before:
                Color(*get_color_from_hex(SECONDARY_COLOR))
                Rectangle(pos=y_coord.pos, size=y_coord.size)
            
            coordinates.add_widget(x_coord)
            coordinates.add_widget(y_coord)
            
            detection_item.add_widget(detection_label)
            detection_item.add_widget(coordinates)
            detection_item.bind(pos=self._update_item_canvas, size=self._update_item_canvas)
            
            self.add_widget(detection_item)
    
    def _update_item_canvas(self, instance, value):
        instance.canvas.before.clear()
        with instance.canvas.before:
            # Background
            Color(*get_color_from_hex("#EBF5FB"))
            Rectangle(pos=instance.pos, size=instance.size)
            
            # Left border
            Color(*get_color_from_hex(SECONDARY_COLOR))
            Rectangle(
                pos=instance.pos,
                size=(dp(4), instance.height)
            )


class ConnectionScreen(Screen):
    def __init__(self, **kwargs):
        super(ConnectionScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(BACKGROUND_COLOR))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Header
        header = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(80),
            padding=[0, dp(10)]
        )
        
        title_label = Label(
            text="AIDRONe Drowning Detection",
            font_size=dp(24),
            color=get_color_from_hex(PRIMARY_COLOR),
            bold=True,
            size_hint_y=None,
            height=dp(40)
        )
        
        subtitle_label = Label(
            text="Connect to your AIDRONe device",
            font_size=dp(16),
            color=get_color_from_hex("#7f8c8d"),
            size_hint_y=None,
            height=dp(30)
        )
        
        header.add_widget(title_label)
        header.add_widget(subtitle_label)
        
        # Connection form
        form_layout = BoxLayout(orientation='vertical', spacing=dp(15), padding=[0, dp(20)])
        
        self.ip_input = TextInput(
            hint_text="Enter WebSocket URL (e.g., ws://192.168.1.100:8765)",
            multiline=False,
            size_hint=(1, None),
            height=dp(50),
            font_size=dp(16),
            padding=[dp(10), dp(12), 0, 0]
        )
        
        # Connect button with custom style
        self.connect_button = Button(
            text="Connect",
            size_hint=(1, None),
            height=dp(50),
            background_normal='',
            background_color=get_color_from_hex(SECONDARY_COLOR),
            color=(1, 1, 1, 1),
            font_size=dp(18),
            bold=True
        )
        self.connect_button.bind(on_press=self.connect_to_websocket)
        
        # Connection status
        self.status_label = Label(
            text="",
            color=get_color_from_hex("#7f8c8d"),
            size_hint_y=None,
            height=dp(30),
            halign='center'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        
        # About section
        about_layout = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(60),
            padding=[dp(10), dp(10)]
        )
        
        about_label = Label(
            text="AIDRONe uses advanced AI to detect drowning incidents\nand send immediate alerts.",
            font_size=dp(14),
            color=get_color_from_hex("#7f8c8d"),
            halign='center'
        )
        about_label.bind(size=about_label.setter('text_size'))
        
        about_layout.add_widget(about_label)
        
        # Add all layouts to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(form_layout)
        
        form_layout.add_widget(self.ip_input)
        form_layout.add_widget(self.connect_button)
        form_layout.add_widget(self.status_label)
        
        main_layout.add_widget(about_layout)
        
        # Footer
        footer = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(40),
            padding=[0, dp(10)]
        )
        
        footer_label = Label(
            text="© 2025 Quantum Bits FLL - Drowning Detection System",
            font_size=dp(12),
            color=get_color_from_hex("#7f8c8d")
        )
        
        footer.add_widget(footer_label)
        main_layout.add_widget(footer)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def connect_to_websocket(self, instance):
        ip_address = self.ip_input.text.strip()
        if not ip_address:
            ip_address = "ws://localhost:8765"  # Default from client.html
        
        # Show connecting status
        self.status_label.text = "Connecting to AIDRONe system..."
        self.status_label.color = get_color_from_hex("#7f8c8d")
        self.connect_button.disabled = True
        
        app = App.get_running_app()
        app.websocket_url = ip_address
        app.connect_to_websocket(
            on_success=self.on_connection_success,
            on_error=self.on_connection_error
        )
    
    def on_connection_success(self):
        self.status_label.text = "Connected! Waiting for alarms..."
        self.status_label.color = get_color_from_hex(SUCCESS_COLOR)
        # Don't transition yet - wait for alarm
    
    def on_connection_error(self, error_msg):
        self.status_label.text = f"Connection error: {error_msg}"
        self.status_label.color = get_color_from_hex(ALERT_COLOR)
        self.connect_button.disabled = False


class WaitingScreen(Screen):
    def __init__(self, **kwargs):
        super(WaitingScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(BACKGROUND_COLOR))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(15))
        
        # Header
        title_label = Label(
            text="AIDRONe Standby Mode",
            font_size=dp(24),
            color=get_color_from_hex(PRIMARY_COLOR),
            bold=True,
            size_hint_y=None,
            height=dp(60)
        )
        
        # Status indicator
        self.status_indicator = StatusIndicator(
            size_hint_y=None,
            height=dp(30)
        )
        self.status_indicator.update_status(True, "Connected - Waiting for alerts")
        
        # Waiting message
        waiting_container = BoxLayout(
            orientation='vertical',
            padding=dp(20),
            size_hint_y=None,
            height=dp(200)
        )
        
        with waiting_container.canvas.before:
            Color(*get_color_from_hex(CARD_BACKGROUND))
            self.waiting_rect = Rectangle(size=waiting_container.size, pos=waiting_container.pos)
        waiting_container.bind(size=self._update_waiting_rect, pos=self._update_waiting_rect)
        
        waiting_icon = Label(
            text="🔍",
            font_size=dp(48),
            size_hint_y=None,
            height=dp(60)
        )
        
        waiting_text = Label(
            text="Monitoring Pool for Drowning Incidents",
            font_size=dp(18),
            color=get_color_from_hex(PRIMARY_COLOR),
            size_hint_y=None,
            height=dp(40),
            halign='center'
        )
        waiting_text.bind(size=waiting_text.setter('text_size'))
        
        waiting_subtext = Label(
            text="You'll be alerted immediately when drowning is detected",
            font_size=dp(14),
            color=get_color_from_hex("#7f8c8d"),
            size_hint_y=None,
            height=dp(60),
            halign='center'
        )
        waiting_subtext.bind(size=waiting_subtext.setter('text_size'))
        
        waiting_container.add_widget(waiting_icon)
        waiting_container.add_widget(waiting_text)
        waiting_container.add_widget(waiting_subtext)
        
        # Disconnect button
        disconnect_button = Button(
            text="Disconnect",
            size_hint=(1, None),
            height=dp(50),
            background_normal='',
            background_color=get_color_from_hex(ALERT_COLOR),
            color=(1, 1, 1, 1)
        )
        disconnect_button.bind(on_press=self.disconnect)
        
        # Add everything to main layout
        main_layout.add_widget(title_label)
        main_layout.add_widget(self.status_indicator)
        main_layout.add_widget(waiting_container)
        main_layout.add_widget(Label(size_hint_y=1))  # Spacer
        main_layout.add_widget(disconnect_button)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def _update_waiting_rect(self, instance, value):
        self.waiting_rect.pos = instance.pos
        self.waiting_rect.size = instance.size
    
    def disconnect(self, instance):
        app = App.get_running_app()
        app.stop_websocket()
        app.root.transition = SlideTransition(direction='right')
        app.root.current = "connection_screen"


class VideoScreen(Screen):
    def __init__(self, **kwargs):
        super(VideoScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(BACKGROUND_COLOR))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # Header
        header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            padding=[dp(10), 0]
        )
        
        title_label = Label(
            text="Drowning Detection System",
            font_size=dp(18),
            color=get_color_from_hex(PRIMARY_COLOR),
            bold=True,
            size_hint_x=0.7,
            halign='left'
        )
        title_label.bind(size=title_label.setter('text_size'))
        
        # Action buttons
        dismiss_button = Button(
            text="Dismiss Alert",
            size_hint=(None, None),
            size=(dp(120), dp(40)),
            background_normal='',
            background_color=get_color_from_hex(SECONDARY_COLOR),
            color=(1, 1, 1, 1)
        )
        dismiss_button.bind(on_press=self.dismiss_alert)
        
        header.add_widget(title_label)
        header.add_widget(dismiss_button)
        
        # Status indicator
        self.status_indicator = StatusIndicator(
            size_hint_y=None,
            height=dp(30)
        )
        
        # Video container
        video_container = BoxLayout(
            orientation='vertical',
            padding=dp(10),
            spacing=0
        )
        
        with video_container.canvas.before:
            Color(*get_color_from_hex(CARD_BACKGROUND))
            self.video_rect = Rectangle(size=video_container.size, pos=video_container.pos)
        video_container.bind(size=self._update_video_rect, pos=self._update_video_rect)
        
        self.image = Image(allow_stretch=True, keep_ratio=True)
        video_container.add_widget(self.image)
        
        # Alert panel
        alert_panel = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(250),
            padding=0
        )
        
        with alert_panel.canvas.before:
            Color(*get_color_from_hex(CARD_BACKGROUND))
            self.alert_rect = Rectangle(size=alert_panel.size, pos=alert_panel.pos)
        alert_panel.bind(size=self._update_alert_rect, pos=self._update_alert_rect)
        
        # Alert header
        alert_header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            padding=[dp(10), 0]
        )
        
        with alert_header.canvas.before:
            Color(*get_color_from_hex(PRIMARY_COLOR))
            self.header_rect = Rectangle(size=alert_header.size, pos=alert_header.pos)
        alert_header.bind(size=self._update_header_rect, pos=self._update_header_rect)
        
        header_label = Label(
            text="📊 Detection Status",
            font_size=dp(16),
            color=(1, 1, 1, 1)
        )
        alert_header.add_widget(header_label)
        
        # Alert content
        alert_content = BoxLayout(orientation='vertical', padding=0)
        
        # Alert message
        self.alert_message = AlertMessage()
        
        # Detection info
        self.detection_info = DetectionInfo()
        
        alert_content.add_widget(self.alert_message)
        alert_content.add_widget(self.detection_info)
        
        alert_panel.add_widget(alert_header)
        alert_panel.add_widget(alert_content)
        
        # Action buttons at bottom
        action_buttons = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            spacing=dp(10),
            padding=[dp(10), dp(5)]
        )
        
        disconnect_button = Button(
            text="Disconnect",
            size_hint_x=0.5,
            background_normal='',
            background_color=get_color_from_hex(ALERT_COLOR),
            color=(1, 1, 1, 1)
        )
        disconnect_button.bind(on_press=self.disconnect)
        
        back_to_standby_button = Button(
            text="Back to Standby",
            size_hint_x=0.5,
            background_normal='',
            background_color=get_color_from_hex("#7f8c8d"),
            color=(1, 1, 1, 1)
        )
        back_to_standby_button.bind(on_press=self.back_to_standby)
        
        action_buttons.add_widget(back_to_standby_button)
        action_buttons.add_widget(disconnect_button)
        
        # Add all layouts to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(self.status_indicator)
        main_layout.add_widget(video_container)
        main_layout.add_widget(alert_panel)
        main_layout.add_widget(action_buttons)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def _update_video_rect(self, instance, value):
        self.video_rect.pos = instance.pos
        self.video_rect.size = instance.size
    
    def _update_alert_rect(self, instance, value):
        self.alert_rect.pos = instance.pos
        self.alert_rect.size = instance.size
    
    def _update_header_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size
    
    def disconnect(self, instance):
        app = App.get_running_app()
        app.stop_websocket()
        app.root.transition = SlideTransition(direction='right')
        app.root.current = "connection_screen"
    
    def back_to_standby(self, instance):
        app = App.get_running_app()
        app.root.transition = SlideTransition(direction='right')
        app.root.current = "waiting_screen"
        self.alert_message.hide()
    
    def dismiss_alert(self, instance):
        # Hide the alert message and update detection info
        self.alert_message.hide()
        self.detection_info.update_detections(None)
        self.status_indicator.update_status(True, "Alert Dismissed - Monitoring Pool")
    
    def update_status(self, status, connected=True):
        self.status_indicator.update_status(connected=connected, text=status)
    
    def update_image(self, image_data):
        # Convert image data to texture
        try:
            # Create a BytesIO object from the image data
            img_buffer = io.BytesIO(image_data)
            
            # Open with PIL and convert to RGBA if needed
            img = PILImage.open(img_buffer)
            
            # Ensure we have the right format for Kivy
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Get the image data as bytes
            width, height = img.size
            img_data = img.tobytes()
            
            # Create a texture with the correct size and format
            if not hasattr(self, 'texture') or self.texture is None or self.texture.width != width or self.texture.height != height:
                self.texture = Texture.create(size=(width, height), colorfmt='rgba')
                self.texture.flip_vertical()
            
            # Update texture with new image data
            self.texture.blit_buffer(img_data, colorfmt='rgba', bufferfmt='ubyte')
            
            # Update the image widget
            self.image.texture = self.texture
        except Exception as e:
            print(f"Error updating image: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def update_detection(self, drowning_detected, drowning_boxes=None):
        if drowning_detected and drowning_boxes:
            self.alert_message.show()
            self.detection_info.update_detections(drowning_boxes)
            self.status_indicator.update_status(False, "ALERT: Drowning Detected!")
        else:
            self.alert_message.hide()
            self.detection_info.update_detections(None)
            self.status_indicator.update_status(True, "System Active - Monitoring Pool")


class AIDRONeApp(App):
    def build(self):
        self.title = "AIDRONe Drowning Detection"
        self.websocket = None
        self.websocket_url = ""
        self.websocket_thread = None
        self.is_running = False
        self.connection_callbacks = {}
        
        # Create screen manager
        self.sm = ScreenManager()
        self.connection_screen = ConnectionScreen(name="connection_screen")
        self.waiting_screen = WaitingScreen(name="waiting_screen")
        self.video_screen = VideoScreen(name="video_screen")
        
        self.sm.add_widget(self.connection_screen)
        self.sm.add_widget(self.waiting_screen)
        self.sm.add_widget(self.video_screen)
        
        # Set theme colors (status bar, etc.)
        self._set_theme_colors()
        
        return self.sm
    
    def _set_theme_colors(self):
        try:
            # Set status bar color on Android
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            window = activity.getWindow()
            
            # Convert hex colors to integer color values
            def hex_to_int_color(hex_color):
                hex_color = hex_color.lstrip('#')
                return int(hex_color, 16) | 0xFF000000
            
            window.setStatusBarColor(hex_to_int_color(PRIMARY_COLOR))
            window.setNavigationBarColor(hex_to_int_color(PRIMARY_COLOR))
        except Exception as e:
            print(f"Could not set theme colors: {e}")
            
    def connect_to_websocket(self, on_success=None, on_error=None):
        self.connection_callbacks = {
            'on_success': on_success,
            'on_error': on_error
        }
        
        if self.is_running:
            return
        
        self.is_running = True
        self.websocket_thread = threading.Thread(target=self.websocket_listener)
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
    
    def websocket_listener(self):
        try:
            # Define WebSocket callbacks
            def on_message(ws, message):
                try:
                    # Try parsing as JSON first (from client.html format)
                    try:
                        data = json.loads(message)
                        
                        # Update image if available
                        if 'image' in data:
                            try:
                                image_data = base64.b64decode(data['image'])
                                # Process image in the main thread
                                Clock.schedule_once(lambda dt: self.video_screen.update_image(image_data), 0)
                            except Exception as img_error:
                                print(f"Error decoding image: {img_error}")
                                import traceback
                                traceback.print_exc()
                        
                        # Handle drowning detection
                        drowning_detected = data.get('drowning_detected', False)
                        drowning_boxes = data.get('drowning_boxes', [])
                        
                        # If drowning is detected and we're not already in video screen, switch to it
                        if drowning_detected and drowning_boxes and self.sm.current != "video_screen":
                            Clock.schedule_once(lambda dt: self.show_video_screen(), 0)
                            
                        # Update the video screen with detection information
                        Clock.schedule_once(
                            lambda dt: self.video_screen.update_detection(drowning_detected, drowning_boxes), 
                            0
                        )
                            
                    except json.JSONDecodeError:
                        # Fallback: assume it's just a base64 image if not JSON
                        try:
                            image_data = base64.b64decode(message)
                            Clock.schedule_once(lambda dt: self.video_screen.update_image(image_data), 0)
                            Clock.schedule_once(lambda dt: self.video_screen.update_detection(False, None), 0)
                        except Exception as b64_error:
                            print(f"Error decoding base64 image: {b64_error}")
                            import traceback
                            traceback.print_exc()
                        
                except Exception as e:
                    print(f"Error processing message: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            def on_error(ws, error):
                print(f"WebSocket error: {error}")
                if self.connection_callbacks.get('on_error'):
                    Clock.schedule_once(
                        lambda dt: self.connection_callbacks['on_error'](str(error)), 
                        0
                    )
                Clock.schedule_once(
                    lambda dt: self.video_screen.update_status(f"Error: {str(error)}", connected=False), 
                    0
                )
            
            def on_close(ws, close_status_code, close_msg):
                print("WebSocket connection closed")
                Clock.schedule_once(
                    lambda dt: self.video_screen.update_status("Disconnected", connected=False), 
                    0
                )
                self.is_running = False
            
            def on_open(ws):
                print("WebSocket connection opened")
                if self.connection_callbacks.get('on_success'):
                    Clock.schedule_once(
                        lambda dt: self.connection_callbacks['on_success'](),
                        0
                    )
                
                # Navigate to waiting screen after successful connection
                Clock.schedule_once(
                    lambda dt: self.show_waiting_screen(), 
                    0
                )
            
            # Create WebSocket connection with improved settings
            import ssl
            websocket.enableTrace(False)  # Disable tracing for better performance
            
            # Create a context with certificate verification disabled
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            # Create WebSocket connection with timeout and ping settings
            self.websocket = websocket.WebSocketApp(
                self.websocket_url,
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            
            # Add ping_interval and ping_timeout
            self.websocket.run_forever(
                ping_interval=10,  # Send ping every 10 seconds
                ping_timeout=5,   # Wait 5 seconds for pong response
                sslopt={"cert_reqs": ssl.CERT_NONE},
                skip_utf8_validation=True  # Skip UTF-8 validation for better performance
            )
            
        except Exception as e:
            print(f"WebSocket thread error: {str(e)}")
            import traceback
            traceback.print_exc()
            if self.connection_callbacks.get('on_error'):
                Clock.schedule_once(
                    lambda dt: self.connection_callbacks['on_error'](str(e)), 
                    0
                )
            self.is_running = False
    
    def show_waiting_screen(self):
        self.sm.transition = SlideTransition(direction='left')
        self.sm.current = "waiting_screen"
    
    def show_video_screen(self):
        self.sm.transition = SlideTransition(direction='left')
        self.sm.current = "video_screen"
        self.video_screen.update_status("ALERT: Drowning Detected!", connected=False)
    
    def stop_websocket(self):
        if self.websocket:
            self.websocket.close()
        self.is_running = False
    
    def on_stop(self):
        self.stop_websocket()

if __name__ == '__main__':
    AIDRONeApp().run()