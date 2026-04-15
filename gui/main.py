import sys
import serial
import time
import os
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject, QUrl, QTimer, QPointF
from PyQt6.QtGraphs import QSplineSeries, QLineSeries

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
speedPointsBuffer = []
setpointPointsBuffer = []
MAX_BUFFER_SIZE = 100  

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
setpointGraphData = graph.findChild(QLineSeries, "setpointGraphData")
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

        addGraphData((time.time() - initializeTime, data), "speed")
        addGraphData((time.time() - initializeTime, setpoint), "setpoint")

        global speedText
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

        # Add latest speed output and setpoint to graph
        addGraphData((time.time() - initializeTime, dataValues[0]), "speed")
        addGraphData((time.time() - initializeTime, dataValues[1]), "setpoint")

        # Update speed and gain text
        speedText.setProperty("text", "Actual Speed: " + str(dataValues[0]) + "rpm")
        kpText.setProperty("text", "Kp: " + str(dataValues[1])) 
        kiText.setProperty("text", "Ki: " + str(dataValues[2]))
        kdText.setProperty("text","Kd: " + str(dataValues[3]))

        return

def getDataFromSerial(data):
    try:
        return [float(x) for x in data.split(',')]
    except:
        return []

def onSliderMoved():
    global setpoint, sliderCooldown
    setpoint = int(600 * setpoint_slider.property("value"))
    setpoint_text.setProperty("text", "Target Speed: " + str(setpoint) + "rpm")
    if time.time() - sliderCooldown > 0.5:  # Limit how often we send commands to avoid overwhelming serial
        sliderCooldown = time.time()
        sendCommand(str(setpoint))

def addGraphData(new_data, destination):
    global speedGraphData, setpointGraphData, graphAxisX

    if isinstance(new_data, tuple):
        x, y = new_data
        new_point = QPointF(x, y)

        match destination:
            case "speed":
                speedPointsBuffer.append(new_point)
                if len(speedPointsBuffer) > MAX_BUFFER_SIZE:
                    speedPointsBuffer.pop(0)
                speedGraphData.replace(speedPointsBuffer)
            case "setpoint":
                setpointPointsBuffer.append(new_point)
                if len(setpointPointsBuffer) > MAX_BUFFER_SIZE:
                    setpointPointsBuffer.pop(0)
                setpointGraphData.replace(setpointPointsBuffer)
            case _:
                print("Invalid destination for graph data. Data not added to graph.")
    
    # Scale x-axis to show last 30 seconds of data
    graphAxisX.setProperty("max", time.time() - initializeTime + 5)
    if time.time() - initializeTime > 10:
        graphAxisX.setProperty("min", time.time() - initializeTime - 10)  

def updateGains(kp, ki, kd):
    kpText.setProperty("text", "Kp: " + str(kp))
    kiText.setProperty("text", "Ki: " + str(ki))
    kdText.setProperty("text", "Kd: " + str(kd))

def sendCommand(command):
    if SIMULATION_MODE or ser is None:
        return
    
    ser.write((command + '\n').encode('utf-8'))

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