import os
import io
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import get_color_from_hex
from kivy.properties import BooleanProperty, StringProperty, ObjectProperty
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.uix.scrollview import ScrollView

# KivyMD imports
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton, MDRectangleFlatIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.icon_definitions import md_icons
from kivymd.uix.button import MDIconButton

import websocket
import threading
import base64
from PIL import Image as PILImage

# Define dark theme colors
DARK_PRIMARY = "#1F1F1F"        # Primary background
DARK_SECONDARY = "#2D2D2D"      # Secondary background (cards)
DARK_ACCENT = "#2196F3"         # Accent color (buttons, highlights)
DARK_ERROR = "#CF6679"          # Error color
DARK_SUCCESS = "#4CAF50"        # Success color
DARK_WARNING = "#FF9800"        # Warning color
DARK_TEXT_PRIMARY = "#FFFFFF"   # Primary text
DARK_TEXT_SECONDARY = "#B0B0B0" # Secondary text
DARK_DIVIDER = "#424242"        # Dividers

class DarkCard(MDCard):
    """A card with modern dark styling"""
    def __init__(self, **kwargs):
        super(DarkCard, self).__init__(**kwargs)
        self.md_bg_color = get_color_from_hex(DARK_SECONDARY)
        self.radius = [dp(8), dp(8), dp(8), dp(8)]
        self.elevation = 1
        self.padding = dp(16)
        self.ripple_behavior = True
        
        # Subtle shadows for depth
        self.shadow_softness = 4
        self.shadow_offset = (0, 1)

class StatusIndicator(BoxLayout):
    def __init__(self, **kwargs):
        super(StatusIndicator, self).__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(36)
        self.padding = [dp(16), 0]
        self.spacing = dp(12)
        
        self.status_dot = BoxLayout()
        self.status_dot.size_hint = (None, None)
        self.status_dot.size = (dp(10), dp(10))
        
        with self.status_dot.canvas:
            Color(*get_color_from_hex(DARK_SUCCESS))
            self.dot = Rectangle(pos=self.status_dot.pos, size=self.status_dot.size)
        
        self.status_text = MDLabel(
            text="System Active",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Caption",
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
                Color(*get_color_from_hex(DARK_SUCCESS))
            else:
                Color(*get_color_from_hex(DARK_ERROR))
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
        self.padding = [dp(8), dp(4)]
        
        with self.canvas.before:
            Color(*get_color_from_hex(DARK_ERROR))
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(4), dp(4), dp(4), dp(4)])
        
        self.message = MDLabel(
            text="DROWNING DETECTED!",  # Removed the warning emoji
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_style="H6",
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
        anim = Animation(opacity=0.7, duration=0.5) + Animation(opacity=1, duration=0.5)
        anim.repeat = True
        anim.start(self)
    
    def stop_pulse_animation(self):
        Animation.cancel_all(self)


class DetectionInfo(ScrollView):
    def __init__(self, **kwargs):
        super(DetectionInfo, self).__init__(**kwargs)
        self.size_hint = (1, 1)
        self.bar_width = dp(4)
        self.bar_color = get_color_from_hex(DARK_ACCENT)
        self.bar_inactive_color = get_color_from_hex(DARK_DIVIDER)
        self.effect_cls = "ScrollEffect"  # Smooth scrolling
        self.scroll_type = ['bars']
        
        self.container = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            spacing=dp(12),
            padding=[dp(8), dp(8)]
        )
        self.container.bind(minimum_height=self.container.setter('height'))
        
        self.no_detection_label = MDLabel(
            text="No drowning incidents detected",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Body1",
            italic=True,
            halign='center',
            valign='middle',
            size_hint_y=None,
            height=dp(40)
        )
        self.no_detection_label.bind(size=self.no_detection_label.setter('text_size'))
        
        self.container.add_widget(self.no_detection_label)
        self.add_widget(self.container)
    
    def update_detections(self, drowning_boxes=None):
        self.container.clear_widgets()
        
        if not drowning_boxes or len(drowning_boxes) == 0:
            self.container.add_widget(self.no_detection_label)
            return
            
        for i, box in enumerate(drowning_boxes):
            detection_card = DarkCard(
                orientation='vertical',
                size_hint_y=None,
                height=dp(100),
                padding=[dp(12), dp(8)]
            )
            
            detection_label = MDLabel(
                text=f"Drowning Person #{i+1}",
                theme_text_color="Custom",
                text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
                font_style="Subtitle1",
                bold=True,
                size_hint_y=None,
                height=dp(30)
            )
            
            coordinates = GridLayout(
                cols=2,
                spacing=[dp(8), dp(8)],
                size_hint_y=None,
                height=dp(50),
                padding=[0, dp(5)]
            )
            
            center_x = box.get('center_x', 0)
            center_y = box.get('center_y', 0)
            
            # Create x coordinate box with proper rectangle reference
            x_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(36)
            )
            
            with x_box.canvas.before:
                Color(*get_color_from_hex(DARK_ACCENT + "33"))
                x_rect = Rectangle(pos=x_box.pos, size=x_box.size)
                x_box.rect = x_rect  # Store reference to rectangle
            
            # Safe binding using the stored reference
            def update_x_rect(instance, value):
                instance.rect.pos = instance.pos
                instance.rect.size = instance.size
            
            x_box.bind(pos=update_x_rect, size=update_x_rect)
            
            x_label = MDLabel(
                text=f"X: {center_x}",
                theme_text_color="Custom",
                text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
                halign='center',
                valign='middle'
            )
            x_box.add_widget(x_label)
            
            # Create y coordinate box with proper rectangle reference
            y_box = BoxLayout(
                orientation='vertical',
                size_hint_y=None,
                height=dp(36)
            )
            
            with y_box.canvas.before:
                Color(*get_color_from_hex(DARK_ACCENT + "33"))
                y_rect = Rectangle(pos=y_box.pos, size=y_box.size)
                y_box.rect = y_rect  # Store reference to rectangle
            
            # Safe binding using the stored reference
            def update_y_rect(instance, value):
                instance.rect.pos = instance.pos
                instance.rect.size = instance.size
            
            y_box.bind(pos=update_y_rect, size=update_y_rect)
            
            y_label = MDLabel(
                text=f"Y: {center_y}",
                theme_text_color="Custom",
                text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
                halign='center',
                valign='middle'
            )
            y_box.add_widget(y_label)
            
            coordinates.add_widget(x_box)
            coordinates.add_widget(y_box)
            
            detection_card.add_widget(detection_label)
            detection_card.add_widget(coordinates)
            
            self.container.add_widget(detection_card)


class ConnectionScreen(Screen):
    def __init__(self, **kwargs):
        super(ConnectionScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(DARK_PRIMARY))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        main_layout = BoxLayout(
            orientation='vertical', 
            padding=[dp(16), dp(32), dp(16), dp(16)],
            spacing=dp(24)
        )
        
        # Header
        header = BoxLayout(
            orientation='vertical', 
            size_hint_y=None, 
            height=dp(80),
            padding=[0, dp(8)]
        )
        
        title_label = MDLabel(
            text="AIDRONe",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
            font_style="H4",
            bold=True,
            size_hint_y=None,
            height=dp(50),
            halign='center'
        )
        
        subtitle_label = MDLabel(
            text="Drowning Detection System",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Subtitle1",
            size_hint_y=None,
            height=dp(30),
            halign='center'
        )
        
        header.add_widget(title_label)
        header.add_widget(subtitle_label)
        
        # Connection form in a card
        form_card = DarkCard(
            orientation='vertical',
            size_hint=(1, None),
            height=dp(190),
            padding=dp(16),
            spacing=dp(20)
        )
        
        self.ip_input = MDTextField(
            hint_text="Enter WebSocket URL",
            mode="rectangle",
            line_color_normal=get_color_from_hex(DARK_DIVIDER),
            line_color_focus=get_color_from_hex(DARK_ACCENT),
            text_color_normal=get_color_from_hex(DARK_TEXT_PRIMARY),
            text_color_focus=get_color_from_hex(DARK_TEXT_PRIMARY),
            hint_text_color_normal=get_color_from_hex(DARK_TEXT_SECONDARY),
            hint_text_color_focus=get_color_from_hex(DARK_ACCENT),
            size_hint=(1, None),
            height=dp(48),
            helper_text="Example: ws://192.168.1.100:8765",
            helper_text_mode="on_focus"
        )
        
        # Connect button (positioned for thumb access)
        self.connect_button = MDRaisedButton(
            text="CONNECT",
            md_bg_color=get_color_from_hex(DARK_ACCENT),
            size_hint=(1, None),
            height=dp(56),
            pos_hint={"center_x": 0.5},
            font_style="Button"
        )
        self.connect_button.bind(on_press=self.connect_to_websocket)
        
        # Connection status
        self.status_label = MDLabel(
            text="",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Caption",
            size_hint_y=None,
            height=dp(24),
            halign='center'
        )
        
        form_card.add_widget(self.ip_input)
        form_card.add_widget(self.connect_button)
        form_card.add_widget(self.status_label)
        
        # Simple about text
        about_label = MDLabel(
            text="AIDRONe uses AI to detect drowning incidents and sends immediate alerts.",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Body2",
            halign='center',
            size_hint_y=None,
            height=dp(60)
        )
        about_label.bind(size=about_label.setter('text_size'))
        
        # Add all layouts to main layout
        main_layout.add_widget(header)
        main_layout.add_widget(form_card)
        main_layout.add_widget(about_label)
        main_layout.add_widget(Label(size_hint_y=1))  # Spacer
        
        # Footer
        footer = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            height=dp(40),
            padding=[0, dp(8)]
        )
        
        footer_label = MDLabel(
            text="© 2025 Quantum Bits FLL",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Caption",
            halign='center',
            size_hint_y=None,
            height=dp(20)
        )
        
        footer.add_widget(footer_label)
        main_layout.add_widget(footer)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def connect_to_websocket(self, instance):
        # Provide feedback that button was pressed
        anim = Animation(md_bg_color=get_color_from_hex(DARK_SUCCESS), duration=0.1) + \
               Animation(md_bg_color=get_color_from_hex(DARK_ACCENT), duration=0.1)
        anim.start(self.connect_button)
        
        ip_address = self.ip_input.text.strip()
        if not ip_address:
            ip_address = "ws://localhost:8765"  # Default
        
        # Show connecting status
        self.status_label.text = "Connecting..."
        self.status_label.theme_text_color = "Custom"
        self.status_label.text_color = get_color_from_hex(DARK_TEXT_SECONDARY)
        self.connect_button.disabled = True
        
        app = MDApp.get_running_app()
        app.websocket_url = ip_address
        app.connect_to_websocket(
            on_success=self.on_connection_success,
            on_error=self.on_connection_error
        )
    
    def on_connection_success(self):
        self.status_label.text = "Connected successfully"
        self.status_label.text_color = get_color_from_hex(DARK_SUCCESS)
        
        # Visual feedback of success
        anim = Animation(md_bg_color=get_color_from_hex(DARK_SUCCESS), duration=0.3)
        anim.start(self.connect_button)
    
    def on_connection_error(self, error_msg):
        self.status_label.text = f"Connection failed"
        self.status_label.text_color = get_color_from_hex(DARK_ERROR)
        self.connect_button.disabled = False
        
        # Visual feedback of error
        anim = Animation(md_bg_color=get_color_from_hex(DARK_ERROR), duration=0.3) + \
               Animation(md_bg_color=get_color_from_hex(DARK_ACCENT), duration=0.3)
        anim.start(self.connect_button)


class WaitingScreen(Screen):
    def __init__(self, **kwargs):
        super(WaitingScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(DARK_PRIMARY))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        # Use a single layout without top bar
        main_layout = BoxLayout(
            orientation='vertical',
            padding=[dp(16), dp(24), dp(16), dp(16)],
            spacing=dp(16)
        )
        
        # Title label to replace header bar
        title_label = MDLabel(
            text="Monitoring",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_ACCENT),
            font_style="H6",
            bold=True,
            size_hint_y=None,
            height=dp(40),
            halign='left'
        )
        
        # Status indicator (now at the top with more prominence)
        self.status_indicator = StatusIndicator(
            size_hint_y=None,
            height=dp(36)
        )
        self.status_indicator.update_status(True, "Connected - Monitoring")
        
        # Waiting message in card
        waiting_card = DarkCard(
            orientation='vertical',
            padding=dp(20),
            size_hint_y=None,
            height=dp(180)
        )
        
        waiting_icon = MDIconButton(
            icon="magnify",
            icon_size=dp(48),
            pos_hint={"center_x": 0.5},
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_PRIMARY)
        )
        
        waiting_text = MDLabel(
            text="Monitoring for Drowning",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
            font_style="H5",
            size_hint_y=None,
            height=dp(40),
            halign='center'
        )
        
        waiting_subtext = MDLabel(
            text="You'll be alerted immediately when drowning is detected",
            theme_text_color="Custom",
            text_color=get_color_from_hex(DARK_TEXT_SECONDARY),
            font_style="Body2",
            size_hint_y=None,
            height=dp(60),
            halign='center'
        )
        
        waiting_card.add_widget(waiting_icon)
        waiting_card.add_widget(waiting_text)
        waiting_card.add_widget(waiting_subtext)
        
        # Add components to main layout
        main_layout.add_widget(title_label)
        main_layout.add_widget(self.status_indicator)
        main_layout.add_widget(waiting_card)
        main_layout.add_widget(Label(size_hint_y=1))  # Spacer
        
        # Disconnect button (positioned at bottom for thumb access)
        disconnect_button = MDRaisedButton(
            text="DISCONNECT",
            md_bg_color=get_color_from_hex(DARK_ERROR),
            size_hint=(1, None),
            height=dp(56)
        )
        disconnect_button.bind(on_press=self.disconnect)
        main_layout.add_widget(disconnect_button)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def disconnect(self, instance):
        # Animation feedback
        anim = Animation(md_bg_color=get_color_from_hex("#D32F2F"), duration=0.1) + \
               Animation(md_bg_color=get_color_from_hex(DARK_ERROR), duration=0.1)
        anim.start(instance)
        
        app = MDApp.get_running_app()
        app.stop_websocket()
        app.root.transition = FadeTransition(duration=0.2)
        app.root.current = "connection_screen"


class VideoScreen(Screen):
    def __init__(self, **kwargs):
        super(VideoScreen, self).__init__(**kwargs)
        
        # Set background color
        with self.canvas.before:
            Color(*get_color_from_hex(DARK_PRIMARY))
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)
        
        main_layout = BoxLayout(orientation='vertical', padding=0, spacing=0)
        
        # Top bar with alarm indication
        top_bar = MDTopAppBar(
            title="Drowning Alert",
            right_action_items=[["close", lambda x: self.dismiss_alert()]],
            md_bg_color=get_color_from_hex(DARK_ERROR),
            specific_text_color=get_color_from_hex(DARK_TEXT_PRIMARY),
            elevation=0
        )
        
        # Content area
        content_area = BoxLayout(
            orientation='vertical',
            padding=[dp(8), dp(8)],
            spacing=dp(8)
        )
        
        # Status indicator
        self.status_indicator = StatusIndicator(
            size_hint_y=None,
            height=dp(36)
        )
        
        # Video card
        video_card = DarkCard(
            orientation='vertical',
            padding=dp(4),
            size_hint_y=0.45
        )
        
        self.image = Image(allow_stretch=True, keep_ratio=True)
        video_card.add_widget(self.image)
        
        # Alert message
        self.alert_message = AlertMessage()
        
        # Detection info panel
        detection_panel = DarkCard(
            orientation='vertical',
            size_hint_y=0.55 - (dp(36) / Window.height) - (dp(80) / Window.height),
            padding=0
        )
        
        # Detection header
        detection_header = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(50),
            padding=[dp(16), 0]
        )
        
        with detection_header.canvas.before:
            Color(*get_color_from_hex(DARK_ACCENT))
            self.header_rect = Rectangle(size=detection_header.size, pos=detection_header.pos)
        detection_header.bind(size=self._update_header_rect, pos=self._update_header_rect)
        
        header_label = MDLabel(
            text="Detection Details",
            theme_text_color="Custom",
            text_color=(1, 1, 1, 1),
            font_style="Subtitle1",
            bold=True
        )
        detection_header.add_widget(header_label)
        
        # Detection content
        self.detection_info = DetectionInfo()
        
        detection_panel.add_widget(detection_header)
        detection_panel.add_widget(self.detection_info)
        
        # Add to content area
        content_area.add_widget(self.status_indicator)
        content_area.add_widget(self.alert_message)
        content_area.add_widget(video_card)
        content_area.add_widget(detection_panel)
        
        # Bottom action buttons
        action_buttons = BoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(80),
            spacing=dp(12),
            padding=[dp(16), dp(16)]
        )
        
        back_to_standby_button = MDRaisedButton(
            text="BACK",
            md_bg_color=get_color_from_hex(DARK_SECONDARY),
            size_hint_x=0.5,
            height=dp(56)
        )
        back_to_standby_button.bind(on_press=self.back_to_standby)
        
        disconnect_button = MDRaisedButton(
            text="DISCONNECT",
            md_bg_color=get_color_from_hex(DARK_ERROR),
            size_hint_x=0.5,
            height=dp(56)
        )
        disconnect_button.bind(on_press=self.disconnect)
        
        action_buttons.add_widget(back_to_standby_button)
        action_buttons.add_widget(disconnect_button)
        
        # Add all layouts to main layout
        main_layout.add_widget(top_bar)
        main_layout.add_widget(content_area)
        main_layout.add_widget(action_buttons)
        
        self.add_widget(main_layout)
    
    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    
    def _update_header_rect(self, instance, value):
        self.header_rect.pos = instance.pos
        self.header_rect.size = instance.size
    
    def disconnect(self, instance):
        # Haptic feedback if available
        try:
            from jnius import autoclass
            vibrator = autoclass('android.os.Vibrator')
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            vibrator = activity.getSystemService(activity.VIBRATOR_SERVICE)
            vibrator.vibrate(50)  # 50ms vibration
        except:
            pass
            
        app = MDApp.get_running_app()
        app.stop_websocket()
        app.root.transition = FadeTransition(duration=0.2)
        app.root.current = "connection_screen"
    
    def back_to_standby(self, instance):
        # Animation feedback
        anim = Animation(md_bg_color=get_color_from_hex("#757575"), duration=0.1) + \
               Animation(md_bg_color=get_color_from_hex(DARK_SECONDARY), duration=0.1)
        anim.start(instance)
        
        app = MDApp.get_running_app()
        app.root.transition = FadeTransition(duration=0.2)
        app.root.current = "waiting_screen"
        self.alert_message.hide()
    
    def dismiss_alert(self):
        # Hide the alert message and update detection info
        self.alert_message.hide()
        self.detection_info.update_detections(None)
        self.status_indicator.update_status(True, "Alert Dismissed - Monitoring")
    
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
            self.status_indicator.update_status(True, "System Active - Monitoring")


class AIDRONeApp(MDApp):
    def build(self):
        # Set app theme to dark
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "BlueGray"
        self.theme_cls.accent_palette = "Blue"
        
        # Hide the title bar/action bar on Android and other platforms
        self.title = ""  # Empty title
        Window.borderless = True  # Remove window border on desktop
        
        # Additional Android-specific title bar hiding
        try:
            from android.runnable import run_on_ui_thread
            from jnius import autoclass
            
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            View = autoclass('android.view.View')
            
            @run_on_ui_thread
            def hide_status_bar(activity):
                decorView = activity.getWindow().getDecorView()
                uiOptions = View.SYSTEM_UI_FLAG_FULLSCREEN
                decorView.setSystemUiVisibility(uiOptions)
            
            hide_status_bar(activity)
        except ImportError:
            # Not on Android, no need for this specific code
            pass
        
        self.websocket = None
        self.websocket_url = ""
        self.websocket_thread = None
        self.is_running = False
        self.connection_callbacks = {}
        
        # Create screen manager with smooth transitions
        self.sm = ScreenManager(transition=FadeTransition(duration=0.2))
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
            # Set status bar color on Android with dark theme
            from jnius import autoclass
            activity = autoclass('org.kivy.android.PythonActivity').mActivity
            window = activity.getWindow()
            
            # Convert hex colors to integer color values
            def hex_to_int_color(hex_color):
                hex_color = hex_color.lstrip('#')
                return int(hex_color, 16) | 0xFF000000
            
            window.setStatusBarColor(hex_to_int_color(DARK_PRIMARY))
            window.setNavigationBarColor(hex_to_int_color(DARK_PRIMARY))
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
                ping_timeout=5,    # Wait 5 seconds for pong response
                sslopt={"cert_reqs": ssl.CERT_NONE},
                skip_utf8_validation=True  # Skip UTF-8 validation for better performance
            )
            
        except Exception as e:
            print(f"WebSocket thread error: {str(e)}")
            import traceback
            traceback.print_exc()
            if self.connection_callbacks.get('on_error'):
                error_message = str(e)  # Capture the error message outside the lambda
                Clock.schedule_once(
                    lambda dt, error=error_message: self.connection_callbacks['on_error'](error),
                    0
                )
            self.is_running = False
    
    def show_waiting_screen(self):
        self.sm.transition = FadeTransition(duration=0.2)
        self.sm.current = "waiting_screen"
    
    def show_video_screen(self):
        self.sm.transition = FadeTransition(duration=0.2)
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