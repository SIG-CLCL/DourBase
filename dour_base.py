from qgis.PyQt.QtWidgets import QAction, QLabel, QDialog, QVBoxLayout, QMessageBox, QPushButton
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtCore import QSettings, QTimer, Qt
import os
import time
import logging
import sys
from pathlib import Path

# Configuration du logger
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

# Création du formateur
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Configuration du handler pour le fichier
file_handler = logging.FileHandler(os.path.join(log_dir, 'plugin.log'))
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

# Configuration du logger principal
logger = logging.getLogger('DourBase')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.propagate = True  # Évite la propagation vers le logger racine

# Test message
logger.info("DourBase logger initialized")

from .dour_base_dialog import DourBaseDialog
from .theme import DarkTheme, LightTheme
from .utils import get_config_dir

s = QSettings()

class DourBase:
    def __init__(self, iface):
        logger.info("Initializing DourBase")
        self.iface = iface
        self.action = None
        self.dialog = None
        logger.debug("DourBase initialized successfully")

    def initGui(self):
        logger.info("Initializing GUI")
        try:
            plugin_dir = os.path.dirname(__file__)
            icon_path = os.path.join(plugin_dir, "assets", "icons", "icon.svg")
            if not os.path.exists(icon_path):
                logger.warning(f"Icon not found at: {icon_path}")
            self.action = QAction(QIcon(icon_path), "DourBase", self.iface.mainWindow())
            logger.debug("Main action created")
        except Exception as e:
            logger.error(f"Error initializing interface: {str(e)}", exc_info=True)
            raise

        try:
            self.action.triggered.connect(self.run)
            self.iface.addToolBarIcon(self.action)
            self.iface.addPluginToMenu("&DourBase", self.action)
            logger.info("Plugin added to toolbar and menu")
        except Exception as e:
            logger.error(f"Error adding plugin to interface: {str(e)}", exc_info=True)
            raise

    def reset_csv_dir(self):
        s.setValue("DourBase/csv_dir", "%INTERNAL%")

    def unload(self):
        logger.info("Unloading plugin")
        try:
            self.iface.removeToolBarIcon(self.action)
            self.iface.removePluginMenu("&DourBase", self.action)
            logger.info("Plugin removed from interface")
        except Exception as e:
            logger.error(f"Error unloading plugin: {str(e)}", exc_info=True)
            raise

    def run(self):
        logger.info("Starting DourBase plugin")
        try:
            valeur = s.value("DourBase/is_first_start", "False")
            plugin_dir = os.path.dirname(__file__)
            is_test_mode = s.value("DourBase/is_test_mode", False)
            logger.debug(f"Test mode: {is_test_mode}, First start: {valeur}")
        except Exception as e:
            logger.error(f"Error reading settings: {str(e)}", exc_info=True)
            raise

        if valeur == "False":
            logger.info("First start detected, showing welcome banner")
            s.setValue("DourBase/is_first_start", "True")
            try:
                # Afficher la bannière pendant 5 secondes
                banner_dialog = QDialog(self.iface.mainWindow())
                DarkTheme.apply(banner_dialog)
                logger.debug("Welcome banner displayed")
            except Exception as e:
                logger.error(f"Error displaying welcome banner: {str(e)}", exc_info=True)
            banner_dialog.setWindowFlags(banner_dialog.windowFlags() | Qt.FramelessWindowHint)
            layout = QVBoxLayout()
            label = QLabel()
            pixmap = QPixmap(os.path.join(plugin_dir, "assets", "pictures", "banner.png"))
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



        from .csv_checker import check_csv_files
        result = check_csv_files(get_config_dir())

        has_errors = (
            result.get('success') is False or  # Si success est explicitement False
            bool(result.get('missing_files')) or  # Fichiers manquants
            bool(result.get('list_problems')) or  # Problèmes dans la liste
            any(  # Problèmes dans les fichiers individuels
                file_data.get('valid') is False
                for file_data in result.get('files', {}).values()
            ) or
            result.get('summary', {}).get('with_errors', 0) > 0  # Erreurs dans le résumé
        )

        if has_errors:
            error_msg = ""

            # Afficher les fichiers manquants
            missing_files = [f for f, data in result.get('files', {}).items()
                          if not data.get('exists')]

            if missing_files:
                error_msg += "❌ Fichiers manquants :\n"
                for file in missing_files:
                    error_msg += f"   - {file}\n"
                error_msg += "\n"

            for filename, file_data in result.get('files', {}).items():
                if file_data.get('problems'):
                    error_msg += f"⚠️ Problèmes dans {filename} :\n"
                    for problem in file_data['problems']:
                        clean_problem = problem.split('\n')[0]
                        error_msg += f"   • {clean_problem}\n"
                    error_msg += "\n"
            is_internal_config = True if s.value("DourBase/csv_dir", "%INTERNAL%") == "%INTERNAL%" else False
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setWindowTitle("Erreur de configuration")
            if is_internal_config:
                message = "Cette erreur provient des fichiers interne du plugin. Réinstaller ou mettre à jour le plugin devrait corriger le problème."
            else:
                message = "Réinitialiser au dossier par défaut changera votre dossier de CSV au dossier interne du plugin, ce qui devrait résoudre le problème.\nToutefois, cela ne corrigera pas le problème dans votre dossier personnalisé.\n\nNote : Vous pouvez également corriger le problème manuellement dans le dossier personalisé des csv. appuyez sur le bouton Afficher les Détails pour voir les problèmes identifiés."
            error_dialog.setText("Impossible de démarrer le plugin :")
            error_dialog.setInformativeText(f'Des problèmes ont été détectés dans les fichiers de configuration.\n\n{message}')

            error_dialog.setDetailedText(error_msg.strip())

            if not is_internal_config:
                reset_to_defaul_folder_button = QPushButton("Reset to default folder")
                reset_to_defaul_folder_button.clicked.connect(self.reset_csv_dir)
                error_dialog.addButton(reset_to_defaul_folder_button, QMessageBox.ActionRole)

            if is_test_mode:
                import json
                json_debug = json.dumps(result, indent=2, ensure_ascii=False)
                test_details = "\n\n=== TECHNICAL DETAILS (TEST MODE) ===\n"
                test_details += json_debug
                error_dialog.setDetailedText(f"{error_msg.strip()}{test_details}")

            msg = error_dialog

            msg.setStyleSheet("""
                QMessageBox {
                    min-width: 700px;
                }
                QTextEdit {
                    min-width: 650px;
                    min-height: 150px;
                    font-family: monospace;
                }
            """)
            if not is_internal_config:
                msg.addButton(QMessageBox.Ok)
            msg.exec_()
            return


        self.dialog = DourBaseDialog()
        theme = s.value("DourBase/theme", "light")
        if theme == "light":
            LightTheme.apply(self.dialog)
        else:
            DarkTheme.apply(self.dialog)
            
        try:
            if not self.dialog:
                logger.debug("Creating a new instance of DourBaseDialog")
                self.dialog = DourBaseDialog(self.iface)
            self.dialog.show()
            logger.info("Main window displayed")
        except Exception as e:
            logger.error(f"Error displaying main window: {str(e)}", exc_info=True)
            QMessageBox.critical(
                self.iface.mainWindow(),
                "Error",
                f"Failed to open DourBase: {str(e)}"
            )
        self.dialog.resize(400, 600)
        self.dialog.raise_()
        self.dialog.activateWindow()
