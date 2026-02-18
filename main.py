import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtCore import QObject

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

# Define functions
def onSliderMoved():
    setpoint = int(600 * setpoint_slider.property("value"))
    setpoint_text.setProperty("text", "Target Speed: " + str(setpoint) + "rpm")

# Connect signals to functions
if setpoint_slider:
    setpoint_slider.valueChanged.connect(onSliderMoved)
else:
    print("Setpoint slider not intialized.")

# Exit program when user closes window
sys.exit(app.exec())