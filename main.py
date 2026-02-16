import sys
from PyQt6.QtWidgets import QApplication, QWidget

app = QApplication(sys.argv)

main_window = QWidget()
main_window.setWindowTitle("Twist & Tune")
main_window.setGeometry(100, 100, 800, 600)
main_window.show()

sys.exit(app.exec())