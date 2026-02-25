import sys
import serial
import time
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QTimer
from PyQt6.QtGraphs import QSplineSeries

SIMULATION_MODE = False

if not SIMULATION_MODE:
    try:
        ser = serial.Serial('COM5', 9600)  # Update 'COM3' to your Arduino's port
        time.sleep(2)   #Wait for the serial connection to initialize
        print("Connected to Arduino on COM5")
    except:
        print("Failed to connect to Arduino. Switching to simulation mode.")
        SIMULATION_MODE = True
        ser = None
else:
    ser = None

def updateSerial():
    global ser
    global SIMULATION_MODE

    if SIMULATION_MODE:
        # import random
        # data = random.randint(0, 600)
        data = "In simulation mode, no actual data :"
        print("Simulated data:", data)

        speedText = root.findChild(QObject, "speedText")

        if speedText:
            speedText.setProperty("text", "Actual Speed: " + str(data) + "rpm")

        return
    
    if ser is None:
        print("Serial connection not initialized.")
        return

    if ser.in_waiting > 0:
        data = ser.readline().decode('utf-8').rstrip()
        print("Received data from Arduino:", data)

        speedText = root.findChild(QObject, "speedText")
        if speedText:
            speedText.setProperty("text", "Actual Speed: " + data + "rpm")
        else:
            print("Speed text object not found.")


# Define local variables here
setpoint = 300

# Create windows application
app = QGuiApplication(sys.argv)

# Create instance of Qt engine to handle UI elements
engine = QQmlApplicationEngine()
engine.load("MainWindow.qml")

# Check that UI loaded properly
if not engine.rootObjects():
    sys.exit(-1)

# Define objects from qml code
root = engine.rootObjects()[0]
setpoint_slider = root.findChild(QObject, "setpointSlider")
setpoint_text = root.findChild(QObject, "setpointText")
graph = root.findChild(QObject, "graph")
graphData = graph.findChild(QSplineSeries, "graphData")
kpText = root.findChild(QObject, "kpText")
kiText = root.findChild(QObject, "kiText")
kdText = root.findChild(QObject, "kdText")

# Define functions
def onSliderMoved():
    setpoint = int(600 * setpoint_slider.property("value"))
    setpoint_text.setProperty("text", "Target Speed: " + str(setpoint) + "rpm")

def addGraphData(new_data):
    if isinstance(new_data, tuple) and isinstance(new_data[0], (int, float)) and isinstance(new_data[1], (int, float)):
        graphData.append(new_data[0], new_data[1])
    elif isinstance(new_data, list) and all(isinstance(data, tuple) and isinstance(data[0], (int, float)) and isinstance(data[1], (int, float)) for data in new_data):
        for data in new_data:
            graphData.append(data[0], data[1])
    else:
        print("Invalid data format for graph. Data should be a list of X,Y or a single X,Y.")

def updateGains(kp, ki, kd):
    kpText.setProperty("text", "Kp: " + str(kp))
    kiText.setProperty("text", "Ki: " + str(ki))
    kdText.setProperty("text", "Kd: " + str(kd))

# Connect signals to functions
if setpoint_slider:
    setpoint_slider.valueChanged.connect(onSliderMoved)
else:
    print("Setpoint slider not intialized.")

timer = QTimer()
timer.timeout.connect(updateSerial)
timer.start(100)  # Check for new serial data every 100ms

# Exit program when user closes window
sys.exit(app.exec())