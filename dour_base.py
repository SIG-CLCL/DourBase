from qgis.PyQt.QtWidgets import QAction, QLabel, QDialog, QVBoxLayout
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtCore import QSettings, QTimer, Qt
import os
import time
from .dour_base_dialog import DourBaseDialog
s = QSettings()

class DourBase:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None

    def initGui(self):
        plugin_dir = os.path.dirname(__file__)
        icon_path = os.path.join(plugin_dir, 'icon.svg')
        self.action = QAction(QIcon(icon_path),"Réseaux Imports", self.iface.mainWindow())

        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&Réseaux Imports", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu("&Réseaux Imports", self.action)

    def run(self):
        valeur = s.value("DourBase/is_first_start", "False")
        plugin_dir = os.path.dirname(__file__)

        if valeur == "False":
            s.setValue("DourBase/is_first_start", "True")
            # Afficher la bannière pendant 5 secondes
            banner_dialog = QDialog(self.iface.mainWindow())
            banner_dialog.setWindowFlags(banner_dialog.windowFlags() | Qt.FramelessWindowHint)
            layout = QVBoxLayout()
            label = QLabel()
            pixmap = QPixmap(os.path.join(plugin_dir, "banner.png"))
            label.setPixmap(pixmap)
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)
            banner_dialog.setLayout(layout)
            banner_dialog.resize(pixmap.width(), pixmap.height())
            banner_dialog.show()
            QTimer.singleShot(5000, banner_dialog.accept)
            banner_dialog.exec_()

        if self.dialog is not None:
            self.dialog.close()
            del self.dialog
            self.dialog = None
        self.dialog = DourBaseDialog()
        self.dialog.resize(400, 600)
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

