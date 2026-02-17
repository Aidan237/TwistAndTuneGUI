import sys
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtQml import QQmlApplicationEngine

# You might need to do 'pip install PyQt6-Graphs' in order for the code to run properly

# Create windows application
app = QGuiApplication(sys.argv)

# Create instance of Qt engine to handle UI elements
engine = QQmlApplicationEngine()
engine.load("MainWindow.qml")

# Check that UI loaded properly
if not engine.rootObjects():
    sys.exit(-1)

# Exit program when user closes window
sys.exit(app.exec())