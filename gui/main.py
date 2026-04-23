import sys
import serial
import time
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget, QLabel, QSlider, QPushButton
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
import OpenGL

# DEPENDENCIES:
# pip install pyqt6 pyqtgraph pyserial pyopengl

# Configuration
SIMULATION_MODE = True
MAX_BUFFER_SIZE = 1000

# Global Variables
setpoint = 300
initializeTime = time.time()

# Serial Connection Setup
if not SIMULATION_MODE:
    try:
        com = 'COM5'
        ser = serial.Serial(com, 9600) 
        time.sleep(2)   #Wait for the serial connection to initialize
        print("Connected to Arduino on " + com)
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
    global SIMULATION_MODE

    if SIMULATION_MODE:
        import random
        data = random.randint(30, 570)
        print("Simulated data:", data)

        window.update_plots(time.time() - initializeTime, data, setpoint)
        window.speed_label.setText("Actual Speed: " + str(data) + "rpm")

        return
    
    if ser is None:
        print("Serial connection not initialized.")
        return

    if ser.in_waiting > 0:
        # Read line of data from serial, decode, then split into list of floats
        data = ser.readline().decode('utf-8').rstrip()
        print("Received data from Arduino:", data)
        dataValues = getDataFromSerial(data)

        # Add latest speed output and setpoint to graph
        window.update_plots(time.time() - initializeTime, dataValues[0], dataValues[1])

        # Update speed and gain text
        window.speed_label.setText("Actual Speed: " + str(dataValues[0]) + "rpm")
        window.update_gains(dataValues[1], dataValues[2], dataValues[3])

        return

def getDataFromSerial(data):
    try:
        return [float(x) for x in data.split(',')]
    except:
        return []
    
def sendCommand(command):
    if SIMULATION_MODE or ser is None:
        return
    
    ser.write((command + '\n').encode('utf-8'))

# UI Application Setup
class Dashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Twist & Tune GUI")
        self.resize(1000, 600)

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
        self.button_layout.addSpacing(30)

        self.button_settings = QPushButton("Settings")
        self.button_settings.setFixedSize(100, 30)
        self.button_settings.setStyleSheet(button_style)
        self.button_layout.addWidget(self.button_settings)

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

        # Add UI Elements
        self.speed_label = QLabel("Actual Speed: 0 rpm")
        self.speed_label.setStyleSheet('color: black; font-size: 24px;')
        self.layout.addWidget(self.speed_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.gain_label = QLabel("Kp: 1.0, Ki: 1.0, Kd: 1.0")
        self.gain_label.setStyleSheet('color: black; font-size: 16px;')
        self.layout.addWidget(self.gain_label, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Add Setpoint Slider
        slider_style = """
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                height: 10px;
                background: #00b1a;
                margin: 2px 0;
                border-radius: 4px;
            }

            QSlider::handle:horizontal {
                background: #007bff;   
                border: 1px solid #0056b3;
                width: 18px;
                height: 18px;
                margin: -5px 0;        
                border-radius: 3px;    
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

        # Buffers
        self.x_data = []
        self.y_speed = []
        self.y_setpoint = []

    def on_slider_change(self, value):
        global setpoint
        setpoint = value
        # Trigger your serial send logic here...

    def on_reset_pressed(self):
        global initializeTime
        initializeTime = time.time()
        self.x_data.clear()
        self.y_speed.clear()
        self.y_setpoint.clear()
        self.graph.setXRange(0, 12)

    def update_gains(self, kp, ki, kd):
        self.gain_label.setText("Kp: " + str(kp) + ", Ki: " + str(ki) + ", Kd: " + str(kd))

    def update_plots(self, t, speed, setpoint):
        global MAX_BUFFER_SIZE
        # Append data
        self.x_data.append(t)
        self.y_speed.append(speed)
        self.y_setpoint.append(setpoint)

        # Keep buffer size
        if len(self.x_data) > MAX_BUFFER_SIZE:
            self.x_data.pop(0)
            self.y_speed.pop(0)
            self.y_setpoint.pop(0)

        # Update the lines
        self.speed_plot.setData(self.x_data, self.y_speed)
        self.setpoint_plot.setData(self.x_data, self.y_setpoint)
        
        # Scroll X-axis automatically
        if t > 10:
            self.graph.setXRange(t - 10, t + 2)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = Dashboard()
    window.show()

    timer = QTimer()
    timer.timeout.connect(updateSerial)
    timer.start(100) # 10Hz update rate

    sys.exit(app.exec())