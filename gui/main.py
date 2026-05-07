import sys
import serial
import math
import time
from PyQt6.QtWidgets import QApplication, QCheckBox, QDoubleSpinBox, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QPushButton, QSpinBox
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg

# DEPENDENCIES:
# pip install pyqt6 pyqtgraph pyserial

# Configuration
SIMULATION_MODE = False
MAX_BUFFER_SIZE = 1000
MAX_SUPPORTED_RPM = 600
SETPOINT_MODE = "slider" # Options: slider, step, sine, triangle

# Global Variables
setpoint = 300
prev_setpoint = 300
speed = 0
initialize_time = time.time()
setpoint_max = MAX_SUPPORTED_RPM
setpoint_min = 0
setpoint_period = 5
residual_data = ""

    
def sendCommand(command):
    print("Serial Command Sent: " + command)
    if SIMULATION_MODE or ser is None:
        return
    
    ser.write((command + '\n').encode('utf-8'))

# Serial Connection Setup
if not SIMULATION_MODE:
    try:
        com = 'COM5'
        ser = serial.Serial(com, 115200) 
        time.sleep(2)   #Wait for the serial connection to initialize
        print("Connected to Arduino on " + com)
        sendCommand("S" + str(int(setpoint))) # Send initial setpoint to Arduino
    except:
        print("Failed to connect to Arduino. Switching to simulation mode.")
        SIMULATION_MODE = True
        ser = None
else:
    ser = None

# Functions
def updateSerial():
    global ser
    global window
    global speed
    global setpoint
    global prev_setpoint
    global residual_data
    global SIMULATION_MODE

    if SIMULATION_MODE:
        import random
        data = random.randint(30, 570)

        window.speed_label.setText("Actual Speed: " + str(data) + "rpm")
        speed = data

        if setpoint != prev_setpoint:
            sendCommand("S" + str(int(setpoint)))
            prev_setpoint = setpoint

        return
    
    if ser is None:
        print("Serial connection not initialized.")
        return

    if ser.in_waiting > 0:
        # Read line of data from serial, decode, then split into list of floats
        #data = ser.readline().decode('utf-8').rstrip()
        raw_payload = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')        
        residual_data += raw_payload

        if '\n' in residual_data:
            lines = residual_data.split('\n')
            residual_data = lines.pop()
            latest_line = lines[-1].strip()
            
            if latest_line:
                data = latest_line
                print("Received data from Arduino:", data)
                dataValues = getDataFromSerial(data)


        # Send setpoint command to Arduino
        if setpoint != prev_setpoint:
            sendCommand("S" + str(int(setpoint)))
            prev_setpoint = setpoint

        # Save latest speed value for next graph update
        speed = dataValues[0]

        # Update speed and gain text
        window.speed_label.setText("Actual Speed: " + str(dataValues[0]) + "rpm   -   Setpoint: " + str(int(setpoint)) + "rpm")
        window.update_gains(dataValues[1], dataValues[2], dataValues[3], dataValues[4], dataValues[5], dataValues[6])

        return

def getDataFromSerial(data):
    try:
        return [float(x) for x in data.split(',')]
    except:
        return []

# UI Application Setup
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Twist & Tune GUI")
        self.resize(1000, 600)

        # Attach settings window
        self.settings_window = SettingsWindow(self)

        # Main Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(20, 10, 20, 10)
        self.main_widget.setStyleSheet('background-color: white;')

        # Title
        self.title_label = QLabel("Twist & Tune")
        self.title_label.setStyleSheet('color: black; font-size: 48px; font-weight: bold;')
        self.layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Top Buttons
        button_style = """
            QPushButton {
                background-color: #f5f5f5;      
                color: black;
                border: 1px solid #9e9e9e;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eeeeee;      
                border: 1px solid #757575;      
            }
            QPushButton:pressed {
                background-color: #bdbdbd;      
                border: 2px solid #757575;      
            }
        """

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.button_slider = QPushButton("Settings")
        self.button_slider.setFixedSize(100, 30)
        self.button_slider.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_slider)
        self.button_slider.clicked.connect(self.on_settings_pressed)

        self.button_reset = QPushButton("Reset")
        self.button_reset.setFixedSize(100, 30)
        self.button_reset.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_reset)
        self.button_reset.clicked.connect(self.on_reset_pressed)

        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout)
        self.layout.addSpacing(20)

        # Graph Setup
        self.graph = pg.PlotWidget(useopengl=True)
        self.graph.setBackground('w')
        self.graph.showGrid(x=True, y=True)
        axis_label_style = {'color': 'black', 'font-size': '16pt'}
        self.graph.setLabel('left', 'Speed', units='RPM', **axis_label_style)
        self.graph.setLabel('bottom', 'Time', units='s', **axis_label_style)
        self.graph.getAxis('left').setPen(color='k', width=1)
        self.graph.getAxis('bottom').setPen(color='k', width=1)
        self.graph.getAxis('left').setTextPen('k')
        self.graph.getAxis('bottom').setTextPen('k')

        # Set axis ranges
        self.graph.setYRange(0, 600, padding=0.05) 
        self.graph.setXRange(0, 12)

        # Create line plots
        self.speed_plot = self.graph.plot(pen=pg.mkPen('r', width=2), name="Actual", antialias=True)
        self.setpoint_plot = self.graph.plot(pen=pg.mkPen('b', width=2), name="Setpoint", antialias=True)
        
        self.layout.addWidget(self.graph)

        # Add Gain/Speed Labels
        self.speed_label = QLabel("Actual Speed: 0 rpm")
        self.speed_label.setStyleSheet('color: black; font-size: 24px;')
        self.layout.addWidget(self.speed_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.gain_label = QLabel("Kp: 1.0, Ki: 1.0, Kd: 1.0")
        self.gain_label.setStyleSheet('color: black; font-size: 16px;')
        self.layout.addWidget(self.gain_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Buffers
        self.x_data = []
        self.y_speed = []
        self.y_setpoint = []

    def on_reset_pressed(self):
        global initialize_time
        initialize_time = time.time()
        self.x_data.clear()
        self.y_speed.clear()
        self.y_setpoint.clear()
        self.graph.setXRange(0, 12)
    
    def on_settings_pressed(self):
        if self.settings_window.isVisible():
            self.settings_window.hide()
        else:
            self.settings_window.show()

    def update_gains(self, kp, ki, kd, pp, pi, pd):
        self.gain_label.setText("Kp: " + str(kp) + " (" + str(pp) + "%), Ki: " + str(ki) + " (" + str(pi) + "%), Kd: " + str(kd) + " (" + str(pd) + "%)")

    def calculate_setpoint(self, t):
        global setpoint, SETPOINT_MODE, setpoint_max, setpoint_min, setpoint_period

        if SETPOINT_MODE == "step":
            setpoint = setpoint_max if (t // setpoint_period) % 2 == 0 else setpoint_min
        elif SETPOINT_MODE == "sine":
            setpoint = (setpoint_max - setpoint_min) / 2 * (1 + math.sin(2 * math.pi * t / setpoint_period)) + setpoint_min
        elif SETPOINT_MODE == "triangle":
            cycle_time = t % (2 * setpoint_period)
            if cycle_time < setpoint_period:
                setpoint = (setpoint_max - setpoint_min) / setpoint_period * cycle_time + setpoint_min
            else:
                setpoint = (setpoint_max - setpoint_min) / setpoint_period * (2 * setpoint_period - cycle_time) + setpoint_min

    def update_plots(self):
        global initialize_time, speed, setpoint, MAX_BUFFER_SIZE
        t = time.time() - initialize_time  

        self.calculate_setpoint(t)

        self.x_data.append(t)
        self.y_speed.append(speed)
        self.y_setpoint.append(setpoint)

        # Limit buffer size
        if len(self.x_data) > MAX_BUFFER_SIZE:
            self.x_data.pop(0)
            self.y_speed.pop(0)
            self.y_setpoint.pop(0)

        self.speed_plot.setData(self.x_data, self.y_speed)
        self.setpoint_plot.setData(self.x_data, self.y_setpoint)
        
        # Scroll x-axis
        if t > 10:
            self.graph.setXRange(t - 10, t + 2)

class SettingsWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 300)

        # Main Widget
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)
        self.layout.setContentsMargins(20, 10, 20, 10)
        self.main_widget.setStyleSheet('background-color: white;')

        # Title Text
        self.title_label = QLabel("Settings")
        self.title_label.setStyleSheet('color: black; font-size: 36px; font-weight: bold;')
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.layout.addWidget(self.title_label)
        self.layout.addSpacing(10)

        # Setpoint Mode Buttons
        button_style = """
            QPushButton {
                background-color: #f5f5f5;      
                color: black;
                border: 1px solid #9e9e9e;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #eeeeee;      
                border: 1px solid #757575;      
            }
            QPushButton:pressed {
                background-color: #bdbdbd;      
                border: 2px solid #757575;      
            }
        """

        self.button_layout = QHBoxLayout()
        self.button_layout.addStretch()

        self.button_slider = QPushButton("Slider")
        self.button_slider.setFixedSize(100, 30)
        self.button_slider.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_slider)
        self.button_slider.clicked.connect(lambda: self.on_setpoint_button_pressed("slider"))

        self.button_step = QPushButton("Step")
        self.button_step.setFixedSize(100, 30)
        self.button_step.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_step)
        self.button_step.clicked.connect(lambda: self.on_setpoint_button_pressed("step"))

        self.button_sine = QPushButton("Sine")
        self.button_sine.setFixedSize(100, 30)
        self.button_sine.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_sine)
        self.button_sine.clicked.connect(lambda: self.on_setpoint_button_pressed("sine"))

        self.button_triangle = QPushButton("Triangle")
        self.button_triangle.setFixedSize(100, 30)
        self.button_triangle.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_triangle)
        self.button_triangle.clicked.connect(lambda: self.on_setpoint_button_pressed("triangle"))

        self.button_layout.addStretch()
        self.layout.addLayout(self.button_layout)
        self.layout.addSpacing(20)

        # Setpoint min/max/period settings
        self.value_layout = QHBoxLayout()

        self.min_label = QLabel("Min:")
        self.min_label.setStyleSheet('color: black; font-size: 14px;')
        self.value_layout.addWidget(self.min_label)
        self.min_input = QSpinBox()
        self.min_input.setStyleSheet('color: black; font-size: 14px;')
        self.min_input.setRange(0, MAX_SUPPORTED_RPM)
        self.min_input.setSingleStep(10)
        self.min_input.setValue(setpoint_min)
        self.min_input.setToolTip("Set minimum setpoint value; only affects step, sine, and triangle modes.")
        self.min_input.valueChanged.connect(self.on_setpoint_value_change)
        self.value_layout.addWidget(self.min_input)

        self.max_label = QLabel("Max:")
        self.max_label.setStyleSheet('color: black; font-size: 14px;')
        self.value_layout.addWidget(self.max_label)
        self.max_input = QSpinBox()
        self.max_input.setStyleSheet('color: black; font-size: 14px;')
        self.max_input.setRange(0, MAX_SUPPORTED_RPM)
        self.max_input.setSingleStep(10)
        self.max_input.setValue(setpoint_max)
        self.max_input.setToolTip("Set maximum setpoint value; only affects step, sine, and triangle modes.")
        self.max_input.valueChanged.connect(self.on_setpoint_value_change)
        self.value_layout.addWidget(self.max_input)

        self.period_label = QLabel("Period:")
        self.period_label.setStyleSheet('color: black; font-size: 14px;')
        self.value_layout.addWidget(self.period_label)
        self.period_input = QDoubleSpinBox()
        self.period_input.setStyleSheet('color: black; font-size: 14px;')
        self.period_input.setRange(2.0, 60.0)
        self.period_input.setSingleStep(0.5)
        self.period_input.setValue(setpoint_period)
        self.period_input.setToolTip("Set setpoint period; only affects step, sine, and triangle modes.")
        self.period_input.valueChanged.connect(self.on_setpoint_value_change)
        self.value_layout.addWidget(self.period_input)

        self.layout.addLayout(self.value_layout)
        self.layout.addSpacing(20)

        # Gain settings
        self.gain_layout = QHBoxLayout()
        self.gain_layout.addStretch()

        self.digital_toggle = QCheckBox("")
        self.digital_toggle.setStyleSheet('border: 1px solid #9e9e9e; padding: 2px;')
        self.digital_toggle.setFixedSize(20, 20)
        self.digital_toggle.setToolTip("Enable digital PID mode; needed for gain adjustments.")
        self.digital_toggle.setChecked(False)
        self.digital_toggle.stateChanged.connect(self.on_digital_toggle)
        self.gain_layout.addWidget(self.digital_toggle)

        self.kp_label = QLabel("Kp:")
        self.kp_label.setStyleSheet('color: black; font-size: 14px;')
        self.gain_layout.addWidget(self.kp_label)
        self.kp_input = QDoubleSpinBox()
        self.kp_input.setStyleSheet('color: black; font-size: 14px;')
        self.kp_input.setRange(0.0, 10.0)
        self.kp_input.setValue(0.0)
        self.kp_input.setSingleStep(0.1)
        self.kp_input.setToolTip("Set proportional gain; only affects digital PID mode.")
        self.kp_input.valueChanged.connect(lambda: self.on_gain_value_change("kp"))
        self.gain_layout.addWidget(self.kp_input)

        self.ki_label = QLabel("Ki:")
        self.ki_label.setStyleSheet('color: black; font-size: 14px;')
        self.gain_layout.addWidget(self.ki_label)
        self.ki_input = QDoubleSpinBox()
        self.ki_input.setStyleSheet('color: black; font-size: 14px;')
        self.ki_input.setRange(0.0, 10.0)
        self.ki_input.setValue(0.0)
        self.ki_input.setSingleStep(0.1)
        self.ki_input.setToolTip("Set integral gain; only affects digital PID mode.")
        self.ki_input.valueChanged.connect(lambda: self.on_gain_value_change("ki"))
        self.gain_layout.addWidget(self.ki_input)

        self.kd_label = QLabel("Kd:")
        self.kd_label.setStyleSheet('color: black; font-size: 14px;')
        self.gain_layout.addWidget(self.kd_label)
        self.kd_input = QDoubleSpinBox()
        self.kd_input.setStyleSheet('color: black; font-size: 14px;')
        self.kd_input.setRange(0.0, 10.0)
        self.kd_input.setValue(0.0)
        self.kd_input.setSingleStep(0.1)
        self.kd_input.setToolTip("Set derivative gain; only affects digital PID mode.")
        self.kd_input.valueChanged.connect(lambda: self.on_gain_value_change("kd"))
        self.gain_layout.addWidget(self.kd_input)

        self.gain_layout.addStretch()
        self.layout.addLayout(self.gain_layout)
        self.layout.addSpacing(20)

        # Slider Labels (min, title, max)
        self.slider_label_layout = QHBoxLayout()
        self.slider_label_min = QLabel("0")
        self.slider_label_min.setStyleSheet('color: black; font-size: 14px;')
        self.slider_label_layout.addWidget(self.slider_label_min, alignment=Qt.AlignmentFlag.AlignLeft)

        self.slider_label = QLabel("Setpoint")
        self.slider_label.setStyleSheet('color: black; font-size: 22px; font-weight: bold;')
        self.slider_label_layout.addWidget(self.slider_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.slider_label_max = QLabel(str(MAX_SUPPORTED_RPM))
        self.slider_label_max.setStyleSheet('color: black; font-size: 14px;')
        self.slider_label_layout.addWidget(self.slider_label_max, alignment=Qt.AlignmentFlag.AlignRight)

        self.layout.addLayout(self.slider_label_layout)
        self.layout.addSpacing(5)

        # Setpoint Slider
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                height: 10px;
                background: #f0f0f0;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #ffffff;   
                border: 1px solid #9e9e9e;
                width: 18px;
                height: 18px;
                margin: -5px 0;        
                border-radius: 1px;    
            }

            QSlider::handle:horizontal:hover {
                background: #0056b3;   
            }
        """

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 600)
        self.slider.setValue(300)
        self.slider.setStyleSheet(slider_style)
        self.layout.addWidget(self.slider)
        self.slider.valueChanged.connect(self.on_slider_change)

        self.layout.addStretch() # Push elements to top

    def on_setpoint_button_pressed(self, mode):
        global SETPOINT_MODE
        SETPOINT_MODE = mode
    
    def on_digital_toggle(self):
        if self.digital_toggle.isChecked():
            sendCommand("M1") # Enable digital PID mode
            self.digital_toggle.setStyleSheet('border: 1px solid #9e9e9e; padding: 2px; background-color: #999999;')
            # Set gains to override auto mode in microcontroller
            #sendCommand("P" + str(round(self.kp_input.value(), 1)))
            #sendCommand("I" + str(round(self.ki_input.value(), 1)))
            #sendCommand("D" + str(round(self.kd_input.value(), 1)))
        else:
            sendCommand("M0") # Enable analog PID mode
            self.digital_toggle.setStyleSheet('border: 1px solid #9e9e9e; padding: 2px; background-color: none;')

    def on_setpoint_value_change(self):
        global setpoint_min, setpoint_max, setpoint_period
        setpoint_min = self.min_input.value()
        setpoint_max = self.max_input.value()
        setpoint_period = self.period_input.value()

    def on_gain_value_change(self, gain):
        match gain:
            case "kp":
                kp = round(self.kp_input.value(), 1)
                sendCommand("P" + str(kp))
            case "ki":
                ki = round(self.ki_input.value(), 1)
                sendCommand("I" + str(ki))
            case "kd":
                kd = round(self.kd_input.value(), 1)
                sendCommand("D" + str(kd))

    def on_slider_change(self, value):
        global setpoint
        if SETPOINT_MODE == "slider":
            setpoint = value

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.aboutToQuit.connect(lambda: sendCommand("O")) # Tell microcontroller to turn off motor on exit
    
    window = Dashboard()
    window.show()

    timer_plot = QTimer()
    timer_plot.timeout.connect(window.update_plots)
    timer_plot.start(50) # Update plots every 50ms

    timer_serial = QTimer()
    timer_serial.timeout.connect(updateSerial)
    timer_serial.start(100) # Poll serial every 100ms

    sys.exit(app.exec())