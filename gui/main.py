import sys
import serial
import time
import os
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtCore import QTimer
from PyQt6.QtGraphs import QSplineSeries

SIMULATION_MODE = True

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

# Define local variables here
setpoint = 300
initializeTime = time.time()
sliderCooldown = initializeTime

# Create windows application
app = QGuiApplication(sys.argv)

# Create instance of Qt engine to handle UI elements
current_dir = os.path.dirname(os.path.abspath(__file__))
qml_path = os.path.join(current_dir, "MainWindow.qml")
engine = QQmlApplicationEngine()
engine.load(QUrl.fromLocalFile(qml_path))

# Check that UI loaded properly
if not engine.rootObjects():
    sys.exit(-1)

# Define objects from qml code
root = engine.rootObjects()[0]
setpoint_slider = root.findChild(QObject, "setpointSlider")
setpoint_text = root.findChild(QObject, "setpointText")
graph = root.findChild(QObject, "graph")
speedGraphData = graph.findChild(QSplineSeries, "speedGraphData")
setpointGraphData = graph.findChild(QSplineSeries, "setpointGraphData")
graphAxisX = graph.findChild(QObject, "graphAxisX")
speedText = root.findChild(QObject, "speedText")
kpText = root.findChild(QObject, "kpText")
kiText = root.findChild(QObject, "kiText")
kdText = root.findChild(QObject, "kdText")

# Define functions

def updateSerial():
    global ser
    global SIMULATION_MODE

    if SIMULATION_MODE:
        import random
        data = random.randint(0, 600)
        print("Simulated data:", data)
        addGraphData((time.time() - initializeTime, data))

        speedText = root.findChild(QObject, "speedText")

        if speedText:
            speedText.setProperty("text", "Actual Speed: " + str(data) + "rpm")

        return
    
    if ser is None:
        print("Serial connection not initialized.")
        return

    if ser.in_waiting > 0:
        # Read line of data from serial, decode, then split into list of floats
        data = ser.readline().decode('utf-8').rstrip()
        print("Received data from Arduino:", data)
        dataValues = getDataFromSerial(data)

        # Add latest speed output to graph
        addGraphData((time.time() - initializeTime, dataValues[0]))

        # Update speed and gain text
        speedText.setProperty("text", "Actual Speed: " + str(dataValues[0]) + "rpm")
        kpText.setProperty("text", "Kp: " + str(dataValues[1])) 
        kiText.setProperty("text", "Ki: " + str(dataValues[2]))
        kdText.setProperty("text","Kd: " + str(dataValues[3]))

        return

def getDataFromSerial(data):
    dataString = ""
    dataList = []

    for c in data:
        if c != ',':
            dataString += c
        else:
            dataList.append(float(dataString))
            dataString = ""

    return dataList

def onSliderMoved():
    setpoint = int(600 * setpoint_slider.property("value"))
    setpoint_text.setProperty("text", "Target Speed: " + str(setpoint) + "rpm")
    if time.time() - sliderCooldown > 0.5:  # Limit how often we send commands to avoid overwhelming serial
        sliderCooldown = time.time()
        sendCommand("S" + str(setpoint))

def addGraphData(new_data):
    if isinstance(new_data, tuple) and isinstance(new_data[0], (int, float)) and isinstance(new_data[1], (int, float)):
        speedGraphData.append(new_data[0], new_data[1])
    elif isinstance(new_data, list) and all(isinstance(data, tuple) and isinstance(data[0], (int, float)) and isinstance(data[1], (int, float)) for data in new_data):
        for data in new_data:
            speedGraphData.append(data[0], data[1])
    else:
        print("Invalid data format for graph. Data should be a list of X,Y or a single X,Y.")
    
    # Scale x-axis to show last 30 seconds of data
    graphAxisX.setProperty("max", time.time() - initializeTime + 5)
    if time.time() - initializeTime > 15:
        graphAxisX.setProperty("min", time.time() - initializeTime - 10)  

def updateGains(kp, ki, kd):
    kpText.setProperty("text", "Kp: " + str(kp))
    kiText.setProperty("text", "Ki: " + str(ki))
    kdText.setProperty("text", "Kd: " + str(kd))

def sendCommand(command):
    if SIMULATION_MODE:
        print("Command " + command + "not sent: In simulation mode.")
    elif ser is None:
        print("Command " + command + " not sent: Serial connection not initialized.")
    else:
        commandString = '<' + command + '>'
        ser.write(commandString.encode('utf-8'))

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