import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject
from PyQt6.QtGraphs import QSplineSeries

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

# Connect signals to functions
if setpoint_slider:
    setpoint_slider.valueChanged.connect(onSliderMoved)
else:
    print("Setpoint slider not intialized.")

# Exit program when user closes window
sys.exit(app.exec())