
from qgis.PyQt import QtGui, QtCore, QtWidgets

class LightTheme:
    @staticmethod
    def apply(widget):
        light_palette = QtGui.QPalette()
        light_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(240, 240, 240))
        light_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.black)
        light_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
        light_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(240, 240, 240))
        light_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.white)
        light_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.black)
        light_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.black)
        light_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(240, 240, 240))
        light_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.black)
        light_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        light_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        light_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        light_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
        
        # Appliquer à tous les widgets
        def apply_palette(w):
            w.setPalette(light_palette)
            for child in w.children():
                if isinstance(child, QtWidgets.QWidget):
                    apply_palette(child)
        
        apply_palette(widget)
        widget.setStyleSheet("""
            QWidget {
                background-color: #F0F0F0;
                color: #000000;
            }
            QPushButton {
                background-color: #F0F0F0;
                border: 1px solid #A0A0A0;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #E0E0E0;
            }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {
                background-color: #FFFFFF;
                border: 1px solid #A0A0A0;
                padding: 3px;
                border-radius: 3px;
            }
            QTabWidget::pane {
                border: 1px solid #A0A0A0;
                background: #F0F0F0;
            }
            QTabBar::tab {
                background: #E0E0E0;
                padding: 5px;
                border: 1px solid #A0A0A0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #F0F0F0;
                border-bottom: 1px solid #F0F0F0;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                border: none;
                background: #F0F0F0;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #C0C0C0;
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                height: 0px;
                width: 0px;
            }
            /* Styles pour le calendrier */
            QCalendarWidget {
                background-color: #FFFFFF;
                color: #000000;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #F0F0F0;
            }
            QCalendarWidget QToolButton {
                background-color: #F0F0F0;
                color: #000000;
                font-weight: bold;
                border: 1px solid #A0A0A0;
                border-radius: 3px;
                padding: 3px;
            }
            QCalendarWidget QMenu {
                background-color: #F0F0F0;
                color: #000000;
            }
            QCalendarWidget {
                background-color: #FFFFFF;
                color: #000000;
                border: 1px solid #A0A0A0;
                border-radius: 3px;
                padding: 2px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #000000;
                background-color: #FFFFFF;
                selection-background-color: #2A82DA;
                selection-color: #FFFFFF;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #A0A0A0;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                width: 0px;
                border: none;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
            }
        """)

class DarkTheme:
    @staticmethod
    def apply(widget):
        dark_palette = QtGui.QPalette()
        dark_palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
        dark_palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.black)
        dark_palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
        dark_palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
        dark_palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
        dark_palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
        dark_palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
        dark_palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.white)
        
        # Appliquer à tous les widgets
        def apply_palette(w):
            w.setPalette(dark_palette)
            for child in w.children():
                if isinstance(child, QtWidgets.QWidget):
                    apply_palette(child)
        
        apply_palette(widget)
        widget.setStyleSheet("""
            QCalendarWidget {
                background-color: #252525;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            QCalendarWidget QWidget {
                alternate-background-color: #353535;
            }
            QCalendarWidget QToolButton {
                background-color: #404040;
                color: #FFFFFF;
                font-weight: bold;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 3px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #505050;
                border: 1px solid #707070;
            }
            QCalendarWidget QMenu {
                background-color: #404040;
                color: #FFFFFF;
                border: 1px solid #555555;
            }
            QCalendarWidget {
                background-color: #353535;
                color: #FFFFFF;
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 2px;
            }
            QCalendarWidget QAbstractItemView:enabled {
                color: #FFFFFF;
                background-color: #252525;
                selection-background-color: #2A82DA;
                selection-color: #FFFFFF;
                alternate-background-color: #353535;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #707070;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                width: 0px;
                border: none;
            }
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 0px;
                border: none;
            }
            QCalendarWidget QAbstractItemView:selected {
                background-color: #2A82DA;
                color: #FFFFFF;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: #353535;
                border-bottom: 1px solid #555555;
            }
            QWidget {
                background-color: #353535;
                color: #FFFFFF;
            }
            QPushButton {
                background-color: #404040;
                border: 1px solid #555555;
                color: #FFFFFF;
                padding: 5px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #505050;
                border: 1px solid #707070;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QLineEdit, QComboBox, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox, QDateEdit, QDateTimeEdit {
                background-color: #252525;
                color: #FFFFFF;
                border: 1px solid #555555;
                padding: 3px;
                border-radius: 3px;
                selection-background-color: #2A82DA;
            }
            QLabel {
                color: #FFFFFF;
            }
            QTabWidget::pane {
                border: 1px solid #555555;
                background: #353535;
            }
            QTabBar::tab {
                background: #404040;
                color: #FFFFFF;
                padding: 5px;
                border: 1px solid #555555;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background: #353535;
                border-bottom: 1px solid #353535;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                border: none;
                background: #353535;
                width: 10px;
                margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                height: 0px;
                width: 0px;
            }

        """)

