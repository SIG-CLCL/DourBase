import glob
import logging
import os
import sys
import zipfile
import requests
import subprocess
import tempfile
import certifi
import time
import traceback
import qgis
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QLabel, QCheckBox, QComboBox, QHBoxLayout, QPushButton, QMessageBox,
    QDateEdit, QScrollArea, QWidget, QFileDialog, QInputDialog, QTabWidget, QSpacerItem, QSizePolicy,
    QFormLayout, QDialogButtonBox, QGroupBox, QTextEdit, QFrame, QSpinBox
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtCore import QDate, QSettings, Qt, QSize, QCoreApplication, QRegExp, QTimer
from datetime import datetime
from qgis.PyQt.QtGui import QPalette, QColor, QIcon, QPixmap, QIntValidator

from osgeo import ogr
import psycopg2
from qgis.core import QgsSettings, QgsDataSourceUri, QgsVectorLayer
from .utils import update_file_name, open_config, check_shapefile_completeness, get_shamas, \
    get_filename_without_extension, get_suffix_after_last_underscore, main_prepare_shapefiles, get_param

import logging
logger = logging.getLogger('DourBase')

s = QSettings()
is_test_mode = s.value("DourBase/is_test_mode", False)

# s.setValue("plugin/key", "value")
# valeur = s.value("plugin/key", "def_value")

def save_logs(console_logs, parent=None, import_dir=None):
    """
    Sauvegarde les logs selon le mode configuré :
    1: Enregistrement automatique dans le dossier d'import
    2: Propose d'enregistrer les logs (comportement par défaut)
    3: Pas de logs
    
    Args:
        console_logs (str): Contenu des logs à enregistrer
        parent (QWidget, optional): Widget parent pour les boîtes de dialogue
        import_dir (str, optional): Dossier d'import pour l'enregistrement automatique
    
    Returns:
        str or None: Chemin du fichier de log ou None si non enregistré
    """
    try:
        # Récupération du paramètre avec get_param et gestion des erreurs
        log_setting = get_param("logs")
        log_setting = int(log_setting) if log_setting is not None else 2
        logger.info(f"[save_logs] Log setting: {log_setting}")

    except (ValueError, TypeError):
        log_setting = 2  # Valeur par défaut en cas d'erreur
    
    if log_setting == 3:  # Pas de logs
        return None
    
    # S'assurer que les logs ne sont pas vides
    if not console_logs or not isinstance(console_logs, str):
        logger.warning("[save_logs] Aucun contenu à logger")
        return None
    
    # Mode 1: Enregistrement automatique
    if log_setting == 1:
        if not import_dir or not os.path.isdir(import_dir):
            logger.warning(f"[save_logs] Dossier d'import invalide pour les logs: {import_dir}")
            return None
            
        try:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(import_dir, f"logs_{timestamp}.txt")
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write("Compte rendu du traitement :\n\n" + console_logs)
            
            logger.info(f"[save_logs] Logs enregistrés automatiquement dans : {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"[save_logs] Erreur lors de l'enregistrement automatique des logs: {str(e)}")
            # Fallback au mode proposition si échec
            log_setting = 2
    
    # Mode 2: Proposition d'enregistrement
    if log_setting == 2:
        try:
            filename, _ = QFileDialog.getSaveFileName(
                parent,
                "Sauvegarder les logs",
                "",
                "Fichiers texte (*.txt)"
            )
            
            if filename:
                if not filename.lower().endswith('.txt'):
                    filename += '.txt'
                    
                with open(filename, "w", encoding="utf-8") as f:
                    f.write("Compte rendu du traitement :\n\n" + console_logs)
                
                logger.info(f"[save_logs] Logs enregistrés dans : {filename}")
                return filename
                
        except Exception as e:
            logger.error(f"[save_logs] Erreur lors de l'enregistrement manuel des logs: {str(e)}")
            if parent:
                QMessageBox.critical(
                    parent,
                    "Erreur",
                    f"Impossible d'enregistrer les logs : {str(e)}"
                )
    
    return None

class MessagesBoxes:
    def __init__(self, type):
        super().__init__(type)

    def error(self, title, message, savelog:bool, console_logs=None, folder=None):
        if savelog and console_logs is None:
            raise Exception("When savelog is True, console_logs can't be None.")

        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        if savelog:
            if console_logs is not None:
                console_logs = (
                    "========== Console output ==========\n\n"
                    f"{console_logs}"
                )
            log_param = int(get_param("logs") or "2")
            msg.setText(f"{message}")
            if log_param == 1:
                save_logs(
                    console_logs=console_logs,
                    parent=self,
                    import_dir=folder if folder is not None else (self.FOLDER if hasattr(self, 'FOLDER') else None)
                )
            elif log_param == 2:
                save_button = QPushButton("Sauvegarder les logs")
                save_button.clicked.connect(lambda: save_logs(console_logs, parent=self))
                msg.addButton(save_button, QMessageBox.ActionRole)
        else:

            msg.setText(message)
        msg.addButton(QMessageBox.Ok)
        msg.setIconPixmap(QPixmap(os.path.join(os.path.dirname(os.path.abspath(__file__)),"assets", "icons","error.svg")))
        msg.exec_()

    def succes(self, title, message, savelog:bool, console_logs=None, folder=None):
        """
        Affiche un message de succès avec gestion des logs
        
        Args:
            title (str): Titre de la boîte de dialogue
            message (str): Message à afficher
            savelog (bool): Si True, active la gestion des logs
            console_logs (str, optional): Contenu des logs à sauvegarder
            folder (str, optional): Dossier pour l'enregistrement automatique
        """
        if savelog and console_logs is None:
            raise ValueError("When savelog is True, console_logs can't be None.")
            
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        
        # Gestion des logs si demandé
        if savelog:
            log_param = int(get_param("logs") or "2")
            
            if log_param == 1:
                save_logs(
                    console_logs=console_logs,
                    parent=self,
                    import_dir=folder if folder is not None else (self.FOLDER if hasattr(self, 'FOLDER') else None)
                )
            elif log_param == 2:
                save_button = QPushButton("Sauvegarder les logs")
                save_button.clicked.connect(lambda: save_logs(
                    console_logs=console_logs,
                    parent=self,
                    import_dir=folder if folder is not None else (self.FOLDER if hasattr(self, 'FOLDER') else None)
                ))
                msg.addButton(save_button, QMessageBox.ActionRole)
            
        msg.setText(message)
        msg.addButton(QMessageBox.Ok)
        msg.setIconPixmap(QPixmap(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "succes.svg")))
        msg.exec_()

class LoginDialog(QDialog):
    def __init__(self, parent=None, username_default="", password_default=""):
        super().__init__(parent)
        self.setWindowTitle("Connexion à la base de données")

        self.username_edit = QLineEdit(username_default)
        self.password_edit = QLineEdit(password_default)
        self.password_edit.setEchoMode(QLineEdit.Password)

        layout = QFormLayout(self)
        layout.addRow("Nom d'utilisateur :", self.username_edit)
        layout.addRow("Mot de passe :", self.password_edit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_credentials(self):
        return self.username_edit.text(), self.password_edit.text()

def help_icon_widget(tooltip_text):
    plugin_dir = os.path.dirname(__file__)
    help_icon_path = os.path.join(plugin_dir, "assets", "icons", "help.png")
    label = QLabel()
    pixmap = QPixmap(help_icon_path).scaled(20, 20, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    label.setPixmap(pixmap)
    label.setFixedSize(20, 20)
    label.setToolTip(tooltip_text)
    return label

class DourBaseDialog(QDialog):
    def save_log_setting(self):
        """Sauvegarde le paramètre de log sélectionné"""
        log_setting = self.log_combo.currentData()
        s.setValue("DourBase/logs", str(log_setting))
        
    def on_version_clicked(self, event):
        """Gère les clics sur le numéro de version pour activer/désactiver le mode test"""
        current_time = time.time()
        
        if current_time - self.last_click_time > 1.0:
            self.version_click_count = 0
        
        self.version_click_count += 1
        self.last_click_time = current_time
        
        if self.version_click_count >= 5:
            self.toggle_test_mode()
            self.version_click_count = 0
    
    def toggle_test_mode(self):
        """Bascule l'état du mode test et affiche une notification"""
        current_mode = s.value("DourBase/is_test_mode", False, type=bool)
        new_mode = not current_mode
        s.setValue("DourBase/is_test_mode", new_mode)
        
        global is_test_mode
        is_test_mode = new_mode
        
        mode_text = "activé" if new_mode else "désactivé"
        QMessageBox.information(
            self,
            "Mode Test",
            f"Le mode test a été {mode_text}.",
            QMessageBox.Ok
        )
        
        self.update_deploy_button_state()
        
    def refresh_dev_settings(self):
        """Rafraîchit l'affichage des paramètres de développement"""
        if not hasattr(self, 'settings_text'):
            return
            
        settings = QSettings()
        settings.beginGroup("DourBase")
        
        all_settings = []
        for key in settings.allKeys():
            value = settings.value(key)
            all_settings.append(f"{key} = {value}")
        
        settings.endGroup()
        
        self.settings_text.setPlainText("\n".join(sorted(all_settings)))
    
    def edit_parameter(self):
        """Ouvre une boîte de dialogue pour modifier un paramètre"""
        settings = QSettings()
        settings.beginGroup("DourBase")
        params = settings.allKeys()
        settings.endGroup()
        
        if not params:
            QMessageBox.information(self, "Aucun paramètre", "Aucun paramètre n'est défini.")
            return
        
        param, ok = QInputDialog.getItem(
            self, 
            "Modifier un paramètre", 
            "Sélectionnez le paramètre à modifier:", 
            params, 
            0, 
            False
        )
        
        if not ok or not param:
            return
        
        current_value = s.value(f"DourBase/{param}", "")
        
        new_value, ok = QInputDialog.getText(
            self,
            f"Modifier {param}",
            f"Nouvelle valeur pour {param}:",
            QLineEdit.Normal,
            str(current_value)
        )
        
        if ok and new_value is not None:
            if new_value.lower() in ('true', 'false'):
                new_value = new_value.lower() == 'true'
            elif new_value.isdigit():
                new_value = int(new_value)
            
            s.setValue(f"DourBase/{param}", new_value)
            self.refresh_dev_settings()
            
            if param == "is_test_mode":
                global is_test_mode
                is_test_mode = bool(new_value)
                self.update_deploy_button_state()
                
            QMessageBox.information(
                self,
                "Redémarrage nécessaire",
                "Le paramètre a été modifié.\n\n"
                "Veuillez redémarrer le plugin pour que les changements prennent effet.",
                QMessageBox.Ok
            )
        
    def __init__(self, parent=None):
        super().__init__(parent)
        self.backup_consultation_path = None
        self.backup_travail_path = None
        self.FOLDER = ''
        self._database_password = ""
        self._database_schema = ""
        self.setWindowTitle("DourBase")


        ############################################################
        ##                                                        ##
        ##                      Tab "Imports"                     ##
        ##                                                        ##
        ############################################################


        self.layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.layout.addWidget(self.tabs)

        # Onglet Imports
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)

        # Créer le bouton
        self.select_dir_button = QPushButton("Importer le dossier")
        self.select_dir_button.clicked.connect(self.select_dir)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_dir_button)
        button_layout.addWidget(help_icon_widget("Sélectionner un dossier à importer.\nCe dossier doit contenir les fichiers .shp à importer.\n"))
        self.content_layout.addLayout(button_layout)

        self.num_source_edit = QLineEdit(self)
        self.num_source_edit.setPlaceholderText("Numéro source (ex : 000)")
        self.num_source_edit.setValidator(QIntValidator(1, 999, self))
        self.content_layout.addWidget(QLabel("Numéro source :"))
        num_source_layout = QHBoxLayout()
        num_source_layout.addWidget(self.num_source_edit)
        num_source_layout.addWidget(help_icon_widget("Dernier numéro de série par commune (sur trois caractères)\nCelui-ci sera ajouté/écrasé à BASEDOC en tant que partie de l'ID_SOURCE, ansi qu'aux données des entités."))
        self.content_layout.addLayout(num_source_layout)

        self.content_layout.addWidget(QLabel("Base de données :"))
        self.db_combo = QComboBox()
        db_layout = QHBoxLayout()
        db_layout.addWidget(self.db_combo)
        db_layout.addWidget(help_icon_widget("Base de données de travail"))
        self.content_layout.addLayout(db_layout)

        self.combo_exploitant = QComboBox()
        options = sorted(open_config("EXPLOITANT.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in EXPLOITANT.csv are: {options}")
        for opt in options:
            self.combo_exploitant.addItem(f"{opt[0]} ({opt[1]})",  opt[1])
        self.content_layout.addWidget(QLabel("Exploitant :"))
        combo_exploitant_layout = QHBoxLayout()
        combo_exploitant_layout.addWidget(self.combo_exploitant)
        combo_exploitant_layout.addWidget(help_icon_widget("L'exploitant,\nCelui-ci sera ajouté à BASEDOC et sera écrasé dans les données des récolements."))
        self.content_layout.addLayout(combo_exploitant_layout)

        self.combo_depco = QComboBox()
        options = sorted(open_config("DEPCO.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in DEPCO.csv are: {options}")
        for opt in options:
            self.combo_depco.addItem(f"{opt[0]} ({opt[1]})", (opt[0], opt[1]))
        self.content_layout.addWidget(QLabel("Commune (DEPCO) :"))
        combo_depco_layout = QHBoxLayout()
        combo_depco_layout.addWidget(self.combo_depco)
        combo_depco_layout.addWidget(help_icon_widget("Code INSEE,\nCelui-ci sera ajouté à BASEDOC"))
        self.content_layout.addLayout(combo_depco_layout)

        self.content_layout.addWidget(QLabel("Type de réseau"))
        self.aep_cb = QCheckBox("AEP")
        self.eu_cb = QCheckBox("EU")
        self.epl_cb = QCheckBox("EPL")
        self.aep_cb.stateChanged.connect(self.ensure_one_checked)
        self.eu_cb.stateChanged.connect(self.ensure_one_checked)
        self.epl_cb.stateChanged.connect(self.ensure_one_checked)
        hbox = QHBoxLayout()
        hbox.addWidget(self.aep_cb)
        hbox.addWidget(self.eu_cb)
        hbox.addWidget(self.epl_cb)
        self.setLayout(hbox)
        hbox_layout = QHBoxLayout()
        hbox_layout.addLayout(hbox)
        hbox_layout.addWidget(help_icon_widget("Le type de plan sera ajouté à BASEDOC"))
        self.content_layout.addLayout(hbox_layout)

        self.localisat_edit = QLineEdit(self)
        self.localisat_edit.setPlaceholderText("Rue des...")
        self.content_layout.addWidget(QLabel("Localisation :"))
        localisat_edit_layout = QHBoxLayout()
        localisat_edit_layout.addWidget(self.localisat_edit)
        localisat_edit_layout.addWidget(help_icon_widget("La localisation du plan sera ajoutée à BASEDOC"))
        self.content_layout.addLayout(localisat_edit_layout)

        self.plan_type_edit = QLineEdit(self)
        self.plan_type_edit.setPlaceholderText("Plan de récolement")
        self.content_layout.addWidget(QLabel("Type de plan :"))
        combo_type_plan_layout = QHBoxLayout()
        combo_type_plan_layout.addWidget(self.plan_type_edit)
        combo_type_plan_layout.addWidget(help_icon_widget("Le type de plan sera ajoutée à BASEDOC"))
        self.content_layout.addLayout(combo_type_plan_layout)

        self.b_etude_edit = QLineEdit(self)
        self.b_etude_edit.setPlaceholderText("SADE")
        self.content_layout.addWidget(QLabel("Bureau d'étude :"))
        b_etude_edit_layout = QHBoxLayout()
        b_etude_edit_layout.addWidget(self.b_etude_edit)
        b_etude_edit_layout.addWidget(help_icon_widget("Le bureau d'études,\nCelui-ci sera ajouté à BASEDOC et sera écrasé dans les données des récolements (Auteur)."))
        self.content_layout.addLayout(b_etude_edit_layout)

        self.combo_entreprise = QComboBox()
        options = sorted(open_config("ENTREPRISE.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in ENTREPRISE.csv are: {options}")
        for opt in options:
            self.combo_entreprise.addItem(f"{opt[0]} ({opt[1]})", (opt[0], opt[1]))
        self.content_layout.addWidget(QLabel("Entreprise :"))
        combo_entreprise_layout = QHBoxLayout()
        combo_entreprise_layout.addWidget(self.combo_entreprise)
        combo_entreprise_layout.addWidget(help_icon_widget("L'entreprise,\nCelle-ci sera ajoutée à BASEDOC et sera écrasée dans les données des récolements."))
        self.content_layout.addLayout(combo_entreprise_layout)

        self.date_plan_edit = QDateEdit(self)
        self.date_plan_edit.setCalendarPopup(True)
        self.date_plan_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_plan_edit.setDate(QDate(2025, 1, 1))
        self.content_layout.addWidget(QLabel("Date du plan :"))
        date_plan_edit_layout = QHBoxLayout()
        date_plan_edit_layout.addWidget(self.date_plan_edit)
        date_plan_edit_layout.addWidget(help_icon_widget("Date de plan,\nCelle-ci sera ajoutée à BASEDOC et sera écrasée dans les données des récolements."))
        self.content_layout.addLayout(date_plan_edit_layout)

        self.echelle_edit = QLineEdit(self)
        self.echelle_edit.setPlaceholderText("échelle (ex : 200)")
        self.echelle_edit.setValidator(QIntValidator())
        self.content_layout.addWidget(QLabel("Echelle :"))
        echelle_edit_layout = QHBoxLayout()
        echelle_edit_layout.addWidget(self.echelle_edit)
        echelle_edit_layout.addWidget(help_icon_widget("Celle-ci sera ajoutée à BASEDOC"))
        self.content_layout.addLayout(echelle_edit_layout)

        self.content_layout.addWidget(QLabel("Plan côté ou non"))
        self.cote = QCheckBox("Cote")
        cote_layout = QHBoxLayout()
        cote_layout.addWidget(self.cote)
        cote_layout.addWidget(help_icon_widget("Celle-ci sera ajoutée à BASEDOC"))
        self.content_layout.addLayout(cote_layout)
        self.cote.setChecked(True)

        self.combo_etat = QComboBox()
        options = sorted(open_config("ETAT.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in ETAT.csv are: {options}")
        for opt in options:
            self.combo_etat.addItem(f"{opt[0]} ({opt[0]})", (opt[0], opt[0]))
        self.content_layout.addWidget(QLabel("Type de support :"))
        combo_etat_layout = QHBoxLayout()
        combo_etat_layout.addWidget(self.combo_etat)
        combo_etat_layout.addWidget(help_icon_widget("Celui-ci sera ajouté à BASEDOC"))
        self.content_layout.addLayout(combo_etat_layout)

        self.combo_support = QComboBox()
        options = sorted(open_config("Q_SUPPORT.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in Q_SUPPORT.csv are: {options}")
        for opt in options:
            self.combo_support.addItem(f"{opt[0]} ({opt[0]})", (opt[0], opt[0]))
        self.content_layout.addWidget(QLabel("Qualité du support :"))
        combo_support_layout = QHBoxLayout()
        combo_support_layout.addWidget(self.combo_support)
        combo_support_layout.addWidget(help_icon_widget("Celui-ci sera ajouté à BASEDOC"))
        self.content_layout.addLayout(combo_support_layout)

        self.content_layout.addWidget(QLabel("Utilisation du plan ou non :"))
        self.utilisat = QCheckBox("Utilisation du plan pour la numérisation")
        utilisat_layout = QHBoxLayout()
        utilisat_layout.addWidget(self.utilisat)
        utilisat_layout.addWidget(help_icon_widget("Celui-ci sera ajouté à BASEDOC"))
        self.content_layout.addLayout(utilisat_layout)
        self.utilisat.setChecked(False)

        self.combo_moa = QComboBox()
        options = sorted(open_config("MOA.csv", "config"), key=lambda x: int(x[1]))
        logger.info(f"[DourBaseDialog] options in MOA.csv are: {options}")
        for opt in options:
            self.combo_moa.addItem(f"{opt[0]} ({opt[1]})", opt[1])
        self.content_layout.addWidget(QLabel("MOA :"))
        combo_moa_layout = QHBoxLayout()
        combo_moa_layout.addWidget(self.combo_moa)
        combo_moa_layout.addWidget(help_icon_widget("Maître d'ouvrage,\nCelui-ci sera ajouté à BASEDOC et sera écrasé dans les données des récolements."))
        self.content_layout.addLayout(combo_moa_layout)

        # File name
        self.file_name_edit = QLineEdit(self)
        self.file_name_edit.setReadOnly(False)
        self.content_layout.addWidget(QLabel("Nom de fichier généré :"))
        file_name_edit_layout = QHBoxLayout()
        file_name_edit_layout.addWidget(self.file_name_edit)
        file_name_edit_layout.addWidget(help_icon_widget("L'ID_SOURCE,\nCelui-ci sera ajouté à BASEDOC et sera écrasé dans les données des récolements."))
        self.content_layout.addLayout(file_name_edit_layout)

        # Bouton d'exécution SQL
        self.run_button = QPushButton("Insérer dans la base")
        self.run_button.clicked.connect(self.run_sql)
        self.content_layout.addWidget(self.run_button)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.content_widget)
        self.tabs.addTab(self.scroll_area, "Imports")

        ############################################################
        ##                                                        ##
        ##                Tab "Identifiants GEODIS"               ##
        ##                                                        ##
        ############################################################

        self.identifiants_geodis_tab = QWidget()
        self.identifiants_geodis_tab_layout = QVBoxLayout(self.identifiants_geodis_tab)
        self.identifiants_geodis_tab_layout.setContentsMargins(1, 1, 1, 1)

        self.identifiants_geodis_group = QGroupBox("Identifiants GEODIS")
        self.identifiants_geodis_group_layout = QHBoxLayout(self.identifiants_geodis_group)

        rsxident = qgis.utils.plugins.get("RsxIdent")
        if rsxident:
            self.identifiants_geodis_tab_layout.addWidget(self.identifiants_geodis_group)
            self.identifiants_geodis_tab_layout.addStretch()

            self.run_aep_button = QPushButton()
            self.run_aep_button.clicked.connect(self.run_aep)
            self.run_aep_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "iconn1.png")))
            self.run_aep_button.setIconSize(QSize(25, 25))
            self.identifiants_geodis_group_layout.addWidget(self.run_aep_button)

            self.run_epl_button = QPushButton()
            self.run_epl_button.clicked.connect(self.run_epl)
            self.run_epl_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "iconn2.png")))
            self.run_epl_button.setIconSize(QSize(25, 25))
            self.identifiants_geodis_group_layout.addWidget(self.run_epl_button)

            self.run_eu_button = QPushButton()
            self.run_eu_button.clicked.connect(self.run_eu)
            self.run_eu_button.setIcon(QIcon(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "iconn3.png")))
            self.run_eu_button.setIconSize(QSize(25, 25))
            self.identifiants_geodis_group_layout.addWidget(self.run_eu_button)

        else:
            label = QLabel(
                'Hmmmm. il semblerait que vous n\'ayez pas le plugin \'RsxIndent\' d\'installé. Afin d\'afficher le contenu de cette fenêtre :<br/> '
                '<ul>'
                '<li>Verifiez que vous avez bien le plugin de téléchargé</li>'
                '<li>Verifiez que le plugin est activé</li>'
                '</ul>'
                'Si le plugin n\'est pas installé, vous pouvez l\'installer via le bouton ci-dessous.<br/>Notez que vous devez avoir un accès à internet.'
            )
            label.setTextFormat(Qt.RichText)
            label.setOpenExternalLinks(True)
            label.setWordWrap(True)
            self.install_button = QPushButton("Installer RsxIndent")
            self.install_button.clicked.connect(self.install_rsxindent)
            self.identifiants_geodis_tab_layout.addWidget(self.identifiants_geodis_group)
            self.identifiants_geodis_tab_layout.addStretch()

            self.identifiants_geodis_group_layout.addWidget(label)
            self.identifiants_geodis_tab_layout.addStretch()
            self.identifiants_geodis_tab_layout.addWidget(self.install_button)
        self.tabs.addTab(self.identifiants_geodis_tab, "Identifiants GEODIS")

        ############################################################
        ##                                                        ##
        ##                   Tab "Deployment"                     ##
        ##                                                        ##
        ############################################################


        self.deploy_widget = QWidget()
        self.deploy_layout = QVBoxLayout(self.deploy_widget)
        self.deploy_layout.setAlignment(Qt.AlignTop)


        self.deploy_button = QPushButton("Déployer")
        self.deploy_button.clicked.connect(self.run_deployment)

        self.deploy_layout.addWidget(QLabel("Base de données de travail :"))
        self.db_work_combo = QComboBox()
        self.deploy_layout.addWidget(self.db_work_combo)

        self.deploy_layout.addWidget(QLabel("Base de données de consultation :"))
        self.db_consultation_combo = QComboBox()
        self.deploy_layout.addWidget(self.db_consultation_combo)

        # Ajoute un label d'alerte (caché par défaut)
        self.db_conflict_label = QLabel("⚠️ Les deux bases sélectionnées sont identiques !")
        self.db_conflict_label.setStyleSheet("color: red; font-weight: bold;")
        self.db_conflict_label.hide()
        self.deploy_layout.addWidget(self.db_conflict_label)

        self.deploy_layout.addWidget(QLabel(f"Nom d'utilisateur"))
        self.db_username = QLineEdit()
        self.db_username.textChanged.connect(self.update_deploy_button_state)
        self.deploy_layout.addWidget(self.db_username)

        self.deploy_layout.addWidget(QLabel(f"Mot de passe des bases de données :"))
        self.db_password = QLineEdit()
        self.db_password.setEchoMode(QLineEdit.Password)
        self.db_password.textChanged.connect(self.update_deploy_button_state)
        self.deploy_layout.addWidget(self.db_password)

        self.backup_travail_path_label = QLabel("Sélectionner le dossier de sauvegarde de la base de données de travail.")
        self.deploy_layout.addWidget(self.backup_travail_path_label)

        self.backup_travail_path_button = QPushButton("Select Directory")

        self.backup_travail_path_button.clicked.connect(self.select_directory_postgis)
        self.deploy_layout.addWidget(self.backup_travail_path_button)

        self.backup_consultation_path_label = QLabel("Sélectionner le dossier de sauvegarde de la base de données de consultation.")
        self.deploy_layout.addWidget(self.backup_consultation_path_label)

        self.backup_consultation_path_button = QPushButton("Select Directory")

        self.backup_consultation_path_button.clicked.connect(self.select_directory_consultation)

        self.deploy_layout.addWidget(self.backup_consultation_path_button)

        self.deploy_layout.addWidget(self.deploy_button)

        self.tabs.addTab(self.deploy_widget, "Déploiement")


        ############################################################
        ##                                                        ##
        ##                     Tab "Console"                      ##
        ##                                                        ##
        ############################################################


        # self.add_console_tab() # <-- code d'ajout de l'onglet


        ############################################################
        ##                                                        ##
        ##                  Tab "Configuration"                   ##
        ##                                                        ##
        ############################################################


        self.param_content_widget = QWidget()
        self.param_layout = QVBoxLayout(self.param_content_widget)
        self.param_layout.setAlignment(Qt.AlignTop)
        
        self.param_scroll = QScrollArea()
        self.param_scroll.setWidgetResizable(True)
        self.param_scroll.setWidget(self.param_content_widget)
        
        self.param_widget = QWidget()
        param_main_layout = QVBoxLayout(self.param_widget)
        param_main_layout.addWidget(self.param_scroll)
        
        self.tabs.addTab(self.param_widget, "Configuration")
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setAlignment(Qt.AlignCenter)
        icon_label = QLabel()
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons", "icon.svg")
        pixmap = QPixmap(icon_path)
        if not pixmap.isNull():
            pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pixmap)
        header_layout.addWidget(icon_label)
        
        from .utils import get_plugin_version
        
        # Création du label de version avec un nom d'objet pour le style
        self.version_label = QLabel(f"Version {get_plugin_version()}")
        self.version_label.setStyleSheet("""
            color: #666666; 
            font-size: 10px;
        """)
        
        # Variables pour le comptage des clics
        self.version_click_count = 0
        self.last_click_time = 0
        
        # Activer le suivi des clics de souris
        self.version_label.mousePressEvent = self.on_version_clicked
        header_layout.addWidget(self.version_label)
        
        self.param_layout.addWidget(header_widget)
        
        self.param_layout.addSpacing(10)

        # Section Thème
        self.param_layout.addWidget(QLabel("<b>Thème de l'interface :</b>"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Clair", "light")
        self.theme_combo.addItem("Sombre", "dark")
        
        # Charger le thème actuel
        settings = QSettings()
        current_theme = settings.value("DourBase/theme", "light")
        index = self.theme_combo.findData(current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        
        theme_layout = QHBoxLayout()
        theme_layout.addWidget(QLabel("Apparence :"))
        theme_layout.addWidget(self.theme_combo)
        self.param_layout.addLayout(theme_layout)
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.param_layout.addWidget(separator)
        
        # Section Dossiers
        self.param_layout.addWidget(QLabel("<b>Dossiers de configuration :</b>"))
        
        # Label et champ pour le chemin des CSV
        label = QLabel("Chemin actuel :")
        self.param_layout.addWidget(label)

        # Champ de chemin
        self.dir_path_edit = QLineEdit(self)
        self.dir_path_edit.setReadOnly(True)
        self.dir_path_edit.setMaximumWidth(350)
        self.param_layout.addWidget(self.dir_path_edit)

        # Bouton sélectionner
        self.select_csv_config_dir_button = QPushButton("Sélectionner le dossier des CSV")
        self.select_csv_config_dir_button.setMaximumWidth(250)
        self.select_csv_config_dir_button.clicked.connect(self.select_csv_config_dir)
        self.param_layout.addWidget(self.select_csv_config_dir_button)

        # Bouton réinitialiser
        self.reset_csv_config_dir_button = QPushButton("Réinitialiser le dossier des CSV")
        self.reset_csv_config_dir_button.setMaximumWidth(250)
        self.reset_csv_config_dir_button.clicked.connect(self.reset_csv_config_dir)
        self.param_layout.addWidget(self.reset_csv_config_dir_button)

        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.param_layout.addWidget(separator)

        # Section Logs
        self.options_de_journalisation = (QLabel("<b>Options de journalisation :</b>"))
        self.param_layout.addWidget(self.options_de_journalisation)
        self.log_combo = QComboBox()
        self.log_combo.addItem("1 - Enregistrement automatique des logs", 1)
        self.log_combo.addItem("2 - Proposer d'enregistrer les logs", 2)
        self.log_combo.addItem("3 - Désactiver les logs", 3)
        
        # Charger la valeur sauvegardée ou utiliser 2 par défaut
        saved_log_setting = int(s.value("DourBase/logs", "2"))
        index = self.log_combo.findData(saved_log_setting)
        if index >= 0:
            self.log_combo.setCurrentIndex(index)
            
        self.log_combo.currentIndexChanged.connect(self.save_log_setting)
        self.param_layout.addWidget(QLabel("Comportement des logs :"))
        self.param_layout.addWidget(self.log_combo)
       
        # Mets à jour l’affichage du chemin
        self.update_dir_path_display()
        
        # Séparateur
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        self.param_layout.addWidget(separator)

        # Ajout des contrôles de gestion des logs
        self.options_de_logs = (QLabel("<b>Options de journalisation du plugin :</b>"))
        self.param_layout.addWidget(self.options_de_logs)
        
        # Taille max des fichiers de log (en Mo)
        log_size_layout = QHBoxLayout()
        log_size_layout.addWidget(QLabel("Taille max d'un fichier de log (Mo) :"))
        log_size_layout.addStretch()
        
        self.log_max_size = QSpinBox(self)
        self.log_max_size.setMinimum(1)
        self.log_max_size.setMaximum(10)
        self.log_max_size.setValue(int(get_param("log_max_size_mb") or 5))
        self.log_max_size.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.log_max_size.valueChanged.connect(self.apply_log_settings)
        log_size_layout.addWidget(self.log_max_size, 0, Qt.AlignRight)
        self.param_layout.addLayout(log_size_layout)
        
        # Nombre de fichiers de backup
        backup_count_layout = QHBoxLayout()
        backup_count_layout.addWidget(QLabel("Nombre de fichiers de backup :"))
        backup_count_layout.addStretch()
        
        self.log_backup_count = QSpinBox(self)
        self.log_backup_count.setMinimum(1)
        self.log_backup_count.setMaximum(10)
        self.log_backup_count.setValue(int(get_param("log_backup_count") or 5))
        self.log_backup_count.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.log_backup_count.valueChanged.connect(self.apply_log_settings)
        backup_count_layout.addWidget(self.log_backup_count, 0, Qt.AlignRight)
        self.param_layout.addLayout(backup_count_layout)
        
        # Ajoute un espace extensible en bas pour forcer l'alignement en haut
        self.param_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.export_btn = QPushButton("Exporter les données du plugin")
        self.export_btn.setToolTip("Exporte les logs, paramètres et informations du plugin dans un fichier ZIP")
        self.export_btn.clicked.connect(self.export_plugin_data)
        self.param_layout.addWidget(self.export_btn)
        
        self.dev_group = QGroupBox("🔧 Développement")
        self.dev_layout = QVBoxLayout()
        self.dev_group.setLayout(self.dev_layout)
        self.dev_group.setVisible(False)
        
        self.settings_text = QTextEdit()
        self.settings_text.setReadOnly(True)
        self.settings_text.setMaximumHeight(150)
        self.dev_layout.addWidget(self.settings_text)
        
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh_dev_settings)
        
        self.edit_param_btn = QPushButton("Modifier un paramètre")
        self.edit_param_btn.clicked.connect(self.edit_parameter)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.edit_param_btn)
        self.dev_layout.addLayout(btn_layout)
        
        self.param_layout.addWidget(self.dev_group)
        
        # Lien vers les issues GitHub
        label = QLabel(
            'Pour tout bug, erreur, question ou autre, n\'hésitez pas à ouvrir une issue sur le repo GitHub du plugin : '
            '<a href="https://github.com/SIG-CLCL/DourBase/issues">https://github.com/SIG-CLCL/DourBase/issues</a>'
        )
        label.setTextFormat(Qt.RichText)
        label.setOpenExternalLinks(True)
        label.setWordWrap(True)

        self.param_layout.addWidget(label)
        self.tabs.addTab(self.param_widget, "Paramètres")

        ############################################################
        ##                                                        ##
        ##                       Le reste                         ##
        ##                                                        ##
        ############################################################


        # Connexions pour synchronisation dynamique
        self.combo_depco.currentIndexChanged.connect(self.update_file_name)
        self.num_source_edit.textChanged.connect(self.update_file_name)
        self.aep_cb.stateChanged.connect(self.update_file_name)
        self.eu_cb.stateChanged.connect(self.update_file_name)
        self.epl_cb.stateChanged.connect(self.update_file_name)
        self.db_work_combo.currentIndexChanged.connect(self.update_deploy_button_state)
        self.db_consultation_combo.currentIndexChanged.connect(self.update_deploy_button_state)
        # Initialisation
        self.num_source_edit.setText("001")
        self.aep_cb.setChecked(True)
        self.update_file_name()
        self.num_source_edit.editingFinished.connect(self.format_num_source)

        self.populate_databases()
        self.update_deploy_button_state()

    def get_groupes(self):
        password = self.db_password.text()
        username = self.db_username.text()
        dbname = self.db_work_combo.currentText()
        settings = QgsSettings()
        settings.beginGroup(f"PostgreSQL/connections/{dbname}")
        conn_params = {
            "host": settings.value("host", ""),
            "port": settings.value("port", ""),
            "database": settings.value("database", ""),
            "user": username,
            "password": password,
        }
        groupes = []
        try:
            import psycopg2
            conn = psycopg2.connect(**conn_params)
            cur = conn.cursor()
            cur.execute("SELECT rolname FROM pg_roles WHERE rolcanlogin = false;")
            rows = cur.fetchall()
            groupes = [row[0] for row in rows]
            cur.close()
            conn.close()
        except Exception as e:
            print("Erreur lors de la connexion ou de la requête :", e)
        return groupes

    def add_console_tab(self):
        try:
            self.tabs.removeTab(4)
        except Exception:
            pass

        self.console_widget = QWidget()
        layout = QVBoxLayout(self.console_widget)
        self.console_textedit = QTextEdit()
        self.console_textedit.setReadOnly(True)
        layout.addWidget(self.console_textedit)
        self.console_tab_index = self.tabs.addTab(self.console_widget, "Console")
        self.tabs.setCurrentIndex(self.console_tab_index)

    def log_to_console(self, message):
        logger.info(f"[DourBaseDialog] [log_to_console] {message}")
        # Détection du niveau de log et application de la couleur
        color = None
        html_message = message

        if message.startswith("[INFO]"):
            color = "blue"
            html_message = f'<span style="color:{color};"><b>[INFO]</b></span>{message[6:]}'
        elif message.startswith("[WARNING]"):
            color = "orange"
            html_message = f'<span style="color:{color};"><b>[WARNING]</b></span>{message[9:]}'
        elif message.startswith("[ERROR]"):
            color = "red"
            html_message = f'<span style="color:{color};"><b>[ERROR]</b></span>{message[7:]}'
        elif "Aborting" in message:
            color = "red"

            html_message = message.replace('Aborting', f'<span style="color:{color};"><b>Aborting</b></span>')
        html_message = html_message.replace('\n', '<br>')
        self.console_textedit.append(html_message)
        self.console_textedit.verticalScrollBar().setValue(self.console_textedit.verticalScrollBar().maximum())
        QCoreApplication.processEvents()

    def format_num_source(self):
        text = self.num_source_edit.text()
        if text:
            num = int(text)
            self.num_source_edit.setText(f"{num:03d}")

    def run_aep(self):
        rsxident = qgis.utils.plugins["RsxIdent"]
        if rsxident:
            rsxident.run()

    def run_epl(self):
        rsxident = qgis.utils.plugins["RsxIdent"]
        if rsxident:
            rsxident.run2()

    def run_eu(self):
        rsxident = qgis.utils.plugins["RsxIdent"]
        if rsxident:
            rsxident.run3()

    def select_directory_consultation(self):
        dir_path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))

        if dir_path:
            self.backup_consultation_path_label.setText(f"Dossier sélectionné pour la sauvegarde de la base de données de consultation :\n{dir_path}")
            self.save_dir_path = dir_path
            self.backup_consultation_path = dir_path
            self.update_deploy_button_state()

    def select_directory_postgis(self):
        dir_path = str(QFileDialog.getExistingDirectory(self, "Select Directory"))

        if dir_path:
            self.backup_travail_path_label.setText(f"Dossier sélectionné pour la sauvegarde de la base de données de travail :\n{dir_path}")
            self.backup_travail_path = dir_path
            self.update_deploy_button_state()

    def update_deploy_button_state(self):
        if is_test_mode:
            self.deploy_button.setEnabled(True)
            if hasattr(self, 'dev_group'):
                self.dev_group.setVisible(True)
                self.refresh_dev_settings()
            return
        elif hasattr(self, 'dev_group'):
            self.dev_group.setVisible(False)
        # 1. Vérifier que les champs utilisateur et mot de passe ne sont pas vides
        username_valid = bool(self.db_username.text().strip())
        password_valid = bool(self.db_password.text())
        
        # 2. Vérifier que les deux bases sont sélectionnées et différentes
        work_db = self.db_work_combo.currentText()
        consult_db = self.db_consultation_combo.currentText()
        databases_selected = bool(work_db and consult_db)
        conflict = (work_db == consult_db) and work_db != ""
        self.db_conflict_label.setVisible(conflict)
        
        # 3. Vérifier que les dossiers de backup sont sélectionnés
        backup_travail_text = self.backup_travail_path_label.text()
        backup_consultation_text = self.backup_consultation_path_label.text()
        backup_default_text = "Le dossier sélectionné pour la sauvegarde PostGIS apparaîtra ici."
        backup_path_postgis_valid = backup_travail_text != backup_default_text and hasattr(self, 'backup_travail_path')
        backup_path_consultation_valid = backup_consultation_text != backup_default_text and hasattr(self, 'backup_consultation_path')
        
        # Activer le bouton seulement si toutes les conditions sont remplies
        all_conditions_met = (
            username_valid and 
            password_valid and 
            databases_selected and 
            not conflict and 
            backup_path_postgis_valid and 
            backup_path_consultation_valid
        )
        
        self.deploy_button.setEnabled(all_conditions_met)

    def find_postgres_dirs(self,base_dir):
        try:
            dirs = [
                d for d in os.listdir(base_dir)
                if d.lower().startswith("postgresql-") and os.path.isdir(os.path.join(base_dir, d))
            ]
            return dirs
        except PermissionError:
            self.deploy_button.setEnabled(False)
            return "no_permission"
        except FileNotFoundError:
            self.deploy_button.setEnabled(False)
            return "not_found"

    def select_dir(self):
        self.FOLDER = str(QFileDialog.getExistingDirectory(self, "Select Directory"))
        try:
            check_shapefile_completeness(self.FOLDER)
            QMessageBox.information(self, "Succès", "Dossier importé avec succès")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Erreur", f"Erreur lors de la récupération des fichiers :\n{e}")

    def select_csv_config_dir(self):
        from .csv_checker import check_csv_files
        
        folder = str(QFileDialog.getExistingDirectory(self, "Sélectionner le dossier des fichiers CSV"))
        if not folder:
            return
            
        result = check_csv_files(folder)
        
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
            
            error_dialog = QMessageBox()
            error_dialog.setIcon(QMessageBox.Critical)
            error_dialog.setWindowTitle("Erreur de configuration")
            error_dialog.setText("Impossible d'enregistrer le dossier :")
            error_dialog.setInformativeText("Des problèmes ont été détectés dans les fichiers de configuration.")
            
            error_dialog.setDetailedText(error_msg.strip())
            
            if is_test_mode:
                import json
                json_debug = json.dumps(result, indent=2, ensure_ascii=False)
                test_details = "\n\n=== DÉTAILS TECHNIQUES (MODE TEST) ===\n"
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
            
            msg.exec_()
            return  
            
        # Si tout est OK, enregistrer le dossier
        try:
            s.setValue("DourBase/csv_dir", folder)
            self.dir_path_edit.setText(folder)
            
            # Mettre à jour l'interface si nécessaire
            if hasattr(self, 'update_csv_status'):
                self.update_csv_status()
            
            # En mode test, on affiche les détails techniques
            if is_test_mode:
                import json
                json_debug = json.dumps(result, indent=2, ensure_ascii=False)
                
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Information)
                msg.setWindowTitle("Succès (Mode Test)")
                msg.setText("Le dossier a été enregistré avec succès.")
                msg.setInformativeText("Les fichiers de configuration ont été vérifiés et sont valides.")
                
                # Ajouter le JSON complet pour le débogage
                msg.setDetailedText(f"=== DÉTAILS TECHNIQUES (MODE TEST) ===\n{json_debug}")
                
                # Ajuster la taille de la boîte de dialogue
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
                msg.exec_()
            else:
                # En mode normal, simple message de succès
                QMessageBox.information(
                    self, 
                    "Succès", 
                    "Le dossier a été enregistré avec succès.\n"
                    "Les fichiers de configuration ont été vérifiés et sont valides."
                )
                                  
        except Exception as e:
            error_msg = f"Une erreur est survenue lors de l'enregistrement du dossier :\n{str(e)}"
            
            # En mode test, on ajoute les détails techniques
            if is_test_mode:
                import json
                json_debug = json.dumps(result, indent=2, ensure_ascii=False)
                error_msg += f"\n\n=== DÉTAILS TECHNIQUES (MODE TEST) ===\n{json_debug}"
            
            QMessageBox.critical(self, "Erreur", error_msg)

    def reset_csv_config_dir(self):
        s.setValue("DourBase/csv_dir", "%INTERNAL%")
        self.update_dir_path_display()
        QMessageBox.information(self, "Succès", "Dossier réinitialisé avec succès.\nLes modifications prendront effet après un redémarrage")

    def export_plugin_data(self):
        """Exporte les données du plugin (logs, build infos, configs) dans un fichier ZIP"""
        from .core.export_utils import export_plugin_data
        from qgis.PyQt.QtWidgets import QFileDialog
        from qgis.PyQt.QtCore import QDir
        
        zip_path = export_plugin_data(self)
        
        if zip_path:
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Enregistrer l'export",
                QDir.homePath() + f"/dourbase_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                "Fichiers ZIP (*.zip)"
            )
            
            if save_path:
                try:
                    import shutil
                    shutil.copy2(zip_path, save_path)
                    
                    QMessageBox.information(
                        self,
                        "Export réussi",
                        f"Les données du plugin ont été exportées avec succès vers :\n{save_path}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Erreur",
                        f"Impossible d'enregistrer le fichier :\n{str(e)}"
                    )
                finally:
                    try:
                        os.remove(zip_path)
                    except:
                        pass

    def apply_log_settings(self):
        """Applique les paramètres des logs"""
        try:
            max_size = self.log_max_size.value()
            backup_count = self.log_backup_count.value()
            if not (1 <= max_size <= 99) or not (1 <= backup_count <= 10):
                return
            
            s.setValue("DourBase/log_max_size_mb", max_size)
            s.setValue("DourBase/log_backup_count", backup_count)
            
            status_msg = f"Paramètres des logs mis à jour : {max_size} Mo, {backup_count} fichiers"
            logger.info(f"[DourBaseDialog] [apply_log_settings] {status_msg}")
            
        except ValueError as e:
            logger.error(f"[DourBaseDialog] [apply_log_settings] Valeur invalide : {str(e)}")
        except Exception as e:
            logger.error(f"[DourBaseDialog] [apply_log_settings] Erreur lors de la mise à jour des paramètres des logs: {str(e)}")

    def change_theme(self):
        """Change le thème de l'application en fonction de la sélection"""
        theme = self.theme_combo.currentData()
        settings = QSettings()
        settings.setValue("DourBase/theme", theme)
        
        # Appliquer le thème à la fenêtre principale
        from .theme import LightTheme, DarkTheme
        if theme == "light":
            LightTheme.apply(self)
        else:
            DarkTheme.apply(self)

    def update_dir_path_display(self):
        dir_path = s.value("DourBase/csv_dir", "%INTERNAL%")
        if dir_path == "%INTERNAL%":
            self.dir_path_edit.setText("Dossier de configuration par défaut")
        else:
            self.dir_path_edit.setText(dir_path)

    def populate_databases(self):
        settings = QgsSettings()
        settings.beginGroup("PostgreSQL/connections")
        connections = settings.childGroups()
        for connection in connections:
            # Add connection name to dropdown
            self.db_consultation_combo.addItem(connection)
            self.db_work_combo.addItem(connection)
            self.db_combo.addItem(connection)

        settings.endGroup()

    def get_selected_db_params(self):
        settings = QgsSettings()
        selected = self.db_combo.currentText()
        group = f"PostgreSQL/connections/{selected}"

        settings.beginGroup(group)
        params = {
            "host": settings.value("host", ""),
            "port": settings.value("port", ""),
            "dbname": settings.value("database", ""),
            "user": settings.value("username", ""),
            "password": settings.value("password", ""),
            "schema": settings.value("schema", "")
        }
        settings.endGroup()

        if not params["user"] or not params["password"]:
            dlg = LoginDialog(self, params["user"], params["password"])
            if dlg.exec_() != QDialog.Accepted:
                return None
            user, pw = dlg.get_credentials()
            if not user or not pw:
                return None
            params["user"] = user
            params["password"] = pw
            self._database_user = user
            self._database_password = pw

        # Demande le schéma si manquant
        if hasattr(self, "_database_schema") and self._database_schema:
            params["schema"] = self._database_schema
        else:
            schemas = get_shamas(params["host"], params["port"], params["dbname"], params["user"], params['password'])
            schemas.sort()
            schema, ok = QInputDialog.getItem(
                self, "Schema",
                "Veuillez sélectionner le schéma désiré :",
                schemas, 0, False
            )
            if not ok or not schema:
                return None
            params["schema"] = schema

        return params

    def ensure_one_checked(self):
        # Get the state of all checkboxes
        checkboxes = [self.aep_cb, self.eu_cb, self.epl_cb]
        checked_boxes = [cb for cb in checkboxes if cb.isChecked()]

        # If no checkbox is checked, re-check the sender
        if not checked_boxes:
            sender = self.sender()
            sender.setChecked(True)

    def update_file_name(self):
        depco = self.combo_depco.currentData()
        depco = depco[1]
        num_source = int(self.num_source_edit.text()) if self.num_source_edit.text() else 0
        num_source = f"{num_source:03d}"
        aep = self.aep_cb.isChecked()
        eu = self.eu_cb.isChecked()
        epl = self.epl_cb.isChecked()
        try:
            name = update_file_name(depco, num_source, aep, eu, epl)
        except Exception as e:
            name = f"Erreur : {e}"
        self.file_name_edit.setText(name)

    def count_features_in_db(self, database, schema, table):
        conn = psycopg2.connect(
            dbname=database["dbname"],
            user=database['user'],
            password=database["password"],
            host=database["host"],
            port=database["port"]
        )
        cur = conn.cursor()
        query = 'SELECT COUNT(*) FROM "{}"."{}"'.format(
            psycopg2.extensions.quote_ident(schema, conn),
            psycopg2.extensions.quote_ident(table, conn)
        )
        cur.execute(query)
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count

    def get_allowed_shp_types(self):
        shp_type_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "shp_type.txt")
        try:
            with open(shp_type_file, "r", encoding="utf-8") as f:
                allowed_types = [line.strip().lower() for line in f.readlines()]
            return allowed_types
        except Exception as e:
            self.log_to_console(f"[ERROR] Impossible de lire shp_type.txt : {e}")
            return []

    def is_shp_allowed(self, shpfile):
        allowed_types = self.get_allowed_shp_types()
        shp_name = get_filename_without_extension(shpfile).lower()
        return shp_name in allowed_types

    def upload_to_db(self, shpfile, database):
        if not self.is_shp_allowed(shpfile):
            self.log_to_console(
                f"[WARNING] Le shapefile {shpfile} n'est pas dans la liste des types autorisés. Ignoré.")

            self.report['shp_files_ignored'] = self.report['shp_files_ignored'] + 1
            return

        if not database["password"]:
            QMessageBox.critical(self, "Erreur", "Aucun mot de passe PostgreSQL fourni, connexion annulée.")
            self.log_to_console(f"[ERROR] Aucun mot de passe PostgreSQL fourni, connexion annulée.")
            return

        layer = QgsVectorLayer(shpfile, "", "ogr")
        if not layer.isValid():
            self.log_to_console(f"[ERROR] Failed to load the shapefile : {shpfile}.")
            print("Failed to load the shapefile!")
            return

        layer_name = get_filename_without_extension(shpfile).lower()
        expected = layer.featureCount()  # X

        # 1. Compter avant import
        count_before = self.count_features_in_db(database, database['schema'], layer_name)

        geometry_type = layer.geometryType()

        self.log_to_console(f"[INFO] Geometry Type: {geometry_type}.\n[INFO] layer name : {layer.name}")
        print(f"Geometry Type: {geometry_type}")
        print(layer.name)

        if str(geometry_type) in ("1", "3"):
            nlt_arg = "-nlt PROMOTE_TO_MULTI"
        elif str(geometry_type) == "0":
            nlt_arg = "-nlt POINT"
        else:
            print(f"Geometry type of {shpfile} is unknown. aborting")
            self.log_to_console(f"Geometry type of {shpfile} is unknown. Aborting.")
            return
        password = database['password']
        password = password.replace('"', '\\"')
        command = f"""ogr2ogr.exe -f PostgreSQL "PG:dbname='{database["dbname"]}' host={database["host"]} port={database["port"]} sslmode=disable user={database['user']} password={password}" -lco DIM=2 {shpfile} {get_filename_without_extension(shpfile)} -append -lco GEOMETRY_NAME=geom -lco FID=ID_{get_suffix_after_last_underscore(shpfile)} -nln {database['schema']}.{layer_name} -a_srs EPSG:2154 {nlt_arg}"""
        safe_command = command.replace(
            f"password={password}",
            "password=[PASSWORD HIDDEN FOR SECURITY REASONS]"
        )

        try:
            result = subprocess.run(
                ["ogr2ogr.exe", "-f", "PostgreSQL", 
                 f"PG:dbname='{database['dbname']}' host={database['host']} port={database['port']} sslmode=disable user={database['user']} password={password}",
                 "-lco", "DIM=2", shpfile, get_filename_without_extension(shpfile),
                 "-append", "-lco", "GEOMETRY_NAME=geom", "-lco", f"FID=ID_{get_suffix_after_last_underscore(shpfile)}",
                 "-nln", f"{database['schema']}.{layer_name}", "-a_srs", "EPSG:2154"] + 
                 (["-nlt", nlt_arg.split()[1]] if nlt_arg else []),
                check=True,
                capture_output=True,
                text=True
            )
            self.log_to_console(f"[INFO] Command executed {safe_command}.")
            print(safe_command)
        except subprocess.CalledProcessError as e:
            self.log_to_console(f"[ERROR] Error executing ogr2ogr: {e.stderr}")
            raise

        # 2. Compter après import
        count_after = self.count_features_in_db(database, database['schema'], layer_name)
        inserted = count_after - count_before  # Y

        # 3. Stocker dans le rapport
        if 'entities_per_layer' not in self.report:
            self.report['entities_per_layer'] = {}
        self.report['entities_per_layer'][layer_name] = (inserted, expected)

    def show_report_popup(self):
        entities_info = ""
        if 'entities_per_layer' in self.report:
            entities_info = "\nNombre d'entités ajoutées / attendues :\n"
            for layer, (added, expected) in self.report['entities_per_layer'].items():
                entities_info += f"  - {layer} : {added}/{expected}\n"

        summary = (
            f"Créées : Les couches ont été créées \"telle quelle\", sans modification.\n"
            f"Modifiées : Les couches ont été modifiées (attributs mis à jour) avant d’être importées.\n\n"
            f"ATTENTION ! Le compte rendu ne prend pas en compte les erreurs renvoyées par l'outil ogr2ogr.\n\n\n\n"
            f"Nombre de fichiers .shp à traiter : {self.report['total_layers']}\n"
            f"Nombre de fichiers .shp traités : {self.report['shp_files_processed']}\n"
            f"Nombre de fichiers .shp ignorés : {self.report['shp_files_ignored']}\n"
            f"Nombre de couches créées : {self.report['added_layers']}\n"
            f"Nombre de couches modifiées : {self.report['modified_layers']}\n"
            f"Nombre de fichiers en erreur : {self.report['shp_files_errors']}\n"
            f"{entities_info}"
        )
        console_logs = (
            f"\n\n\n\n\n"
            "========== Console output ==========\n\n"
            f"{self.console_textedit.toPlainText()}"
        )

        msg = QMessageBox(self)
        msg.setWindowTitle("Insertion réussie dans la base !")
        msg.setText("Compte rendu du traitement :\n\n" + summary)

        # Préparation des logs complets
        full_logs = "Compte rendu du traitement :\n\n" + summary + "\nDétails :\n" + "\n".join(self.report.get("logs", []))
        if hasattr(self, 'console_textedit'):
            full_logs += console_logs
        
        # Gestion des logs avec save_logs qui gère déjà tous les cas
        log_param = int(get_param("logs") or "2")
        
        if log_param == 1:
            save_logs(
                console_logs=full_logs,
                parent=self,
                import_dir=self.FOLDER
            )
        elif log_param == 2:
            save_button = QPushButton("Sauvegarder les logs")
            save_button.clicked.connect(lambda: save_logs(
                console_logs=full_logs,
                parent=self,
                import_dir=self.FOLDER if hasattr(self, 'FOLDER') else None
            ))
            msg.addButton(save_button, QMessageBox.ActionRole)

        msg.addButton(QMessageBox.Ok)

        msg.exec_()
        self.tabs.removeTab(4)

    def install_rsxindent(self):
        try:
            print("Installation du plugin RsxIndent")
            download_link = "https://echanges.brest-metropole.fr/VIPDU72/GeoPaysdeBrest/PluginQGIS/RsxIdent.zip"

            if sys.platform.startswith('win'):
                plugins_dir = os.path.join(
                    os.environ['APPDATA'],
                    'QGIS', 'QGIS3', 'profiles', 'default', 'python', 'plugins'
                )
            else:
                plugins_dir = os.path.expanduser('~/.local/share/QGIS/QGIS3/profiles/default/python/plugins')

            if not os.path.exists(plugins_dir):
                os.makedirs(plugins_dir)

            file_name = os.path.join(plugins_dir, "RsxIndent.zip")

            # 1. Télécharger le fichier ZIP
            response = requests.get(download_link, verify=certifi.where(), timeout=30)
            if response.status_code == 200:
                with open(file_name, "wb") as file:
                    file.write(response.content)
                print(f"Fichier téléchargé avec succès sous {file_name}")
            else:
                print(f"Échec du téléchargement. Code: {response.status_code}")
                QMessageBox.criritcal(self, "Échec du téléchargement", f"Échec du téléchargement. Code: {response.status_code}")
                return

            with zipfile.ZipFile(file_name, 'r') as zip_ref:
                zip_ref.extractall(plugins_dir)
            print(f"Plugin extrait dans {plugins_dir}")

            os.remove(file_name)
            print("Fichier ZIP supprimé.")

            print("Installation terminée. Redémarrez QGIS pour activer le plugin.")
            QMessageBox.information(self, "Succès", f"Installation terminée. Redémarrez QGIS pour activer le plugin.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error installing RsxIndent : {e}")

            print(f"[ERROR] Error installing RsxIndent : {e}")

    def run_sql(self):
        self.add_console_tab()
        self.log_to_console("[INFO] Run_sql called")
        if not is_test_mode:
            try:
                database = self.get_selected_db_params()
            except Exception as e:
                if "authentication failed" in str(e).lower():
                    self.log_to_console("[WARNING] Authentification failed")
                    QMessageBox.critical(self, "Erreur d'authentification", 
                                          "Échec de l'authentification.\nVeuillez vérifier votre nom d'utilisateur et votre mot de passe.")
                    self.run_sql()
                    return
                else:
                    self.log_to_console(f"[ERROR] Error getting database params: {e}")
                    MessagesBoxes.error(self, "Erreur de connexion", 
                                        f"Impossible de se connecter à la base de données. Erreur: {e}",savelog=True,console_logs=self.console_textedit.toPlainText(), folder=self.FOLDER)
                    return
            if database is None:
                print("[WARNING] Database is none. Aborting")
                self.log_to_console("[WARNING] Database is none. Aborting")
                return
            try:
                check_shapefile_completeness(self.FOLDER)
            except FileNotFoundError as e:
                # QMessageBox.critical(self, "Erreur",
                #                      f"Erreur lors de la récupération des fichiers :\n{e}\n\nAjout dans la base de données annulé.")
                self.log_to_console(f"[ERROR] Erreur lors de la récupération des fichiers : {e} Ajout dans la base de données annulé.")
                MessagesBoxes.error(self, "Erreur",
                                    f"Erreur lors de la récupération des fichiers :\n{e}\n\nAjout dans la base de données annulé.",
                                    savelog=True,
                                    console_logs=self.console_textedit.toPlainText(), folder=self.FOLDER)
                return


            self.auteur = self.b_etude_edit.text()
            convert_dir = main_prepare_shapefiles(self.FOLDER)
            self.NEW_FOLDER = convert_dir
            self.SHP = os.path.join(self.NEW_FOLDER, '*.shp')
            depco = self.combo_depco.currentData()
            depco = depco[1]
            num_source = self.num_source_edit.text()
            aep = '*' if self.aep_cb.isChecked() else ''
            eu = '*' if self.eu_cb.isChecked() else ''
            epl = '*' if self.epl_cb.isChecked() else ''
            cote = 'Oui' if self.cote.isChecked() else 'Non'
            utilisat = 'Oui' if self.utilisat.isChecked() else 'Non'
            no_origine = ''
            localisat = self.localisat_edit.text().replace("'", "''")
            date_qdate = self.date_plan_edit.date()
            type_plan = self.plan_type_edit.text().replace("'", "''")
            date_str = date_qdate.toString("yyyy-MM-dd")
            b_etude = self.b_etude_edit.text()
            entreprise = self.combo_entreprise.currentData()
            entreprise = entreprise[1]
            echelle = self.echelle_edit.text()
            etat = self.combo_etat.currentData()
            etat = etat[1]
            q_support = self.combo_support.currentData()
            q_support = q_support[1]
            nom_fichier = self.file_name_edit.text()
            moa = self.combo_moa.currentData()
            id_source = str(depco) + '_' + str(num_source)
            exploitant = self.combo_exploitant.currentData()
            hyperliens = './pdf/' + nom_fichier + '.pdf'
            ID_OBJET = None
            ND_AMONT = None
            ND_AVAL = None
            ID_CARG = None
            self.report = {
                "total_layers": 0,
                "added_layers": 0,
                "modified_layers": 0,
                "shp_files_processed": 0,
                "shp_files_errors": 0,
                "shp_files_ignored": 0,
                "logs": []
            }

            shp_files = glob.glob(self.SHP)
            self.report["total_layers"] = len(shp_files)

            text = (
                f"[INFO] Données utilisée dans le traitement : \n"
                f"* auteur : {self.auteur}\n"
                f"* Dossier de sortie : {convert_dir}\n"
                f"* fichiers shp : {self.SHP}\n"
                f"* depco : {depco}\n"
                f"* num_source : {num_source}\n"
                f"* aep : {'non' if aep == '' else 'oui'}\n"
                f"* eu : {'non' if eu == '' else 'oui'}\n"
                f"* epl : {'non' if epl == '' else 'oui'}\n"
                f"* cote : {'non' if cote == '' else 'oui'}\n"
                f"* utilisat : {utilisat}\n"
                f"* no_origine : {'Données vides' if no_origine == '' else no_origine}\n"
                f"* localisat : {'localisat non renseigné' if localisat == '' else localisat}\n"
                f"* date de plan : {date_str}\n"
                f"* type de plan : {'type de plan non renseigné' if type_plan == '' else type_plan}\n"
                f"* bureau d\'étude : {'bureau d\'étude non renseigné' if b_etude == '' else b_etude}\n"
                f"* entreprise {entreprise}\n"
                f"* échelle : {'échelle non renseigné' if echelle == '' else echelle}\n"
                f"* etat : {etat}\n"
                f"* Qualité de support : {q_support}\n"
                f"* nom du fichier : {nom_fichier}\n"
                f"* moa : {moa}\n"
                f"* id source : {id_source}\n"
                f"* exploitant : {exploitant}\n"
                f"* fichiers shp : {shp_files}\n"
            )
            self.log_to_console(text)


            try:
                # Ajout a la basedoc
                if not database["password"]:
                    QMessageBox.critical(self, "Erreur", "Aucun mot de passe PostgreSQL fourni, connexion annulée.")
                    self.log_to_console(
                        f"[ERROR] Aucun mot de passe PostgreSQL fourni, connexion annulée.")
                    return

                try:
                    conn = psycopg2.connect(
                        host=database["host"],
                        dbname=database["dbname"],
                        user=database["user"],
                        password=database["password"],
                        port=database["port"]
                    )
                    cursor = conn.cursor()
                except Exception as e:
                    error_message = str(e)
                    if "authentication failed" in error_message.lower():
                        QMessageBox.critical(self, "Erreur d'authentification", 
                                          "Échec de l'authentification.\nVeuillez vérifier votre nom d'utilisateur et votre mot de passe.")
                        self.log_to_console("[WARNING] Authentification failed")
                        self.run_sql()
                    else:
                        QMessageBox.critical(self, "Erreur de connexion", 
                                          f"Impossible de se connecter à la base de données.\nErreur: {error_message}")
                        self.log_to_console(f"[ERROR] Error connecting to the database: {error_message}")
                    return

                cursor.execute(
                    'SELECT 1 FROM {}.basedoc WHERE id_source = %s'.format(
                        psycopg2.extensions.quote_ident(database['schema'], conn)
                    ),
                    (id_source,)
                )
                exists = cursor.fetchone() is not None

                if exists:
                    self.log_to_console(
                        f"[WARNING] Un enregistrement avec le num_source '{id_source}' existe déjà.\n[INFO] Affichage de la popup de confirmation")
                    reply = QMessageBox.question(
                        self,
                        "Attention",
                        f"Un enregistrement avec le num_source '{id_source}' existe déjà.\nVoulez-vous continuer ?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    self.log_to_console(
                        f"[INFO] Popup displayed")
                    if reply == QMessageBox.No:
                        self.log_to_console(
                            f"[INFO] User answered 'NO'. Aborting")
                        cursor.close()
                        conn.close()
                        return
                    else:
                        self.log_to_console(
                            f"[INFO] User answered 'YES'.")
                        cursor.close()
                        conn.close()
            except Exception as e:
                print(traceback.format_exc())
                self.log_to_console(
                    f"[ERROR] Erreur lors de la verification de la présence de {id_source} dans la base de données : {e}")
                self.log_to_console("[INFO] affichage de la popup de confirmation")
                reply = QMessageBox.question(
                    self,
                    "Woops",
                    f"Désolée. Une erreur est survenue lors de la verification de la présence de {id_source} dans la base de données.\nVoulez-vous continuer ?\n\nNote : l'erreur est visible dans la console, et vous pourez enregistrez la sortie de la console à la fin.",
                    QMessageBox.Yes | QMessageBox.No
                )
                self.log_to_console(
                    f"[INFO] Popup displayed")
                if reply == QMessageBox.No:
                    self.log_to_console(
                        f"[INFO] User answered 'NO'. Aborting")
                    return
                else:
                    self.log_to_console(
                        f"[INFO] User answered 'YES'.")
            try:
                for layer_path in shp_files:
                    print(f"Traitement de la couche : {layer_path}")
                    self.log_to_console(
                        f"[INFO] Traitement de la couche : {layer_path}")
                    try:
                        layer_edit = QgsVectorLayer(layer_path, '', 'ogr')
                        if not layer_edit.isValid():
                            self.report["shp_files_errors"] += 1
                            self.log_to_console(
                                f"[ERROR] Couche invalide {layer_path}")
                            self.report["logs"].append(f"Erreur : Couche invalide {layer_path}")
                            QMessageBox.critical(self, "Erreur",
                                                f"La couche {layer_path} n'est pas valide. Modifications annulées.")
                            continue

                        # Récupération des index de champs (vérifier existence)
                        index_id_source = layer_edit.fields().indexFromName('ID_SOURCE')
                        index_auteur = layer_edit.fields().indexFromName('AUTEUR')
                        index_date_plan = layer_edit.fields().indexFromName('DATE_PLAN')
                        index_moa = layer_edit.fields().indexFromName('MOA')
                        index_exploitant = layer_edit.fields().indexFromName('EXPLOITANT')
                        index_hyperliens = layer_edit.fields().indexFromName('HYPERLIENS')
                        index_id_objet = 0
                        index_nd_amont = layer_edit.fields().indexFromName('ND_AMONT')
                        index_nd_aval = layer_edit.fields().indexFromName('ND_AVAL')
                        index_id_carg = layer_edit.fields().indexFromName('ID_CARG')
                        index_entreprise = layer_edit.fields().indexFromName('ENTREPRISE')
                        # Démarrer l'édition
                        if not layer_edit.startEditing():
                            self.log_to_console(
                                f"[ERROR] Impossible de démarrer l'édition de la couche {layer_path}.")
                            self.report["shp_files_errors"] += 1
                            self.report["logs"].append(f"Erreur : Impossible de démarrer l'édition {layer_path}")
                            QMessageBox.critical(self, "Erreur",
                                                f"Impossible de démarrer l'édition de la couche {layer_path}.")
                            continue

                        try:
                            modified = False
                            for feat in layer_edit.getFeatures():
                                fid = feat.id()
                                if index_id_source >= 0:
                                    layer_edit.changeAttributeValue(fid, index_id_source, id_source)
                                    modified = True
                                if index_auteur >= 0:
                                    layer_edit.changeAttributeValue(fid, index_auteur, self.auteur)
                                    modified = True
                                if index_date_plan >= 0:
                                    layer_edit.changeAttributeValue(fid, index_date_plan,
                                                                    self.date_plan_edit.date().toString("yyyy-MM-dd"))
                                    modified = True
                                if index_moa >= 0:
                                    layer_edit.changeAttributeValue(fid, index_moa, moa)
                                    modified = True
                                if index_exploitant >= 0:
                                    layer_edit.changeAttributeValue(fid, index_exploitant, exploitant)
                                    modified = True
                                if index_hyperliens >= 0:
                                    layer_edit.changeAttributeValue(fid, index_hyperliens,
                                                                    './pdf/' + self.file_name_edit.text() + '.pdf')
                                    modified = True
                                if index_nd_amont >= 0:
                                    layer_edit.changeAttributeValue(fid, index_nd_amont, None)
                                    modified = True
                                if index_nd_aval >= 0:
                                    layer_edit.changeAttributeValue(fid, index_nd_aval, None)
                                    modified = True
                                if index_id_carg >= 0:
                                    layer_edit.changeAttributeValue(fid, index_id_carg, None)
                                    modified = True
                                if index_entreprise >= 0:
                                    layer_edit.changeAttributeValue(fid, index_entreprise, entreprise)
                                    modified = True
                            # Valider les modifications
                            if not layer_edit.commitChanges():
                                raise Exception("Échec de la validation des modifications.")

                            self.report["shp_files_processed"] += 1
                            if modified:
                                self.report["modified_layers"] += 1
                                self.report["logs"].append(f"Modifié : {layer_path}")
                            else:
                                self.report["added_layers"] += 1
                                self.report["logs"].append(f"Ajouté (pas de modif détectée) : {layer_path}")

                        except Exception as e:
                            self.log_to_console(
                                f"[ERROR] Erreur lors de la modification de la couche {layer_path} :\n{str(e)}")
                            self.report["shp_files_errors"] += 1
                            self.report["logs"].append(f"Erreur sur {layer_path} : {str(e)}")
                            QMessageBox.critical(self, "Erreur",
                                                f"Erreur lors de la modification de la couche {layer_path} :\n{str(e)}")
                    except Exception as e:
                        self.log_to_console(
                            f"[ERROR] Error : {str(e)}")
                        print(f"ERROR : {str(e)}")
                        QMessageBox.critical(self, "Erreur",
                                            f"Erreur : {str(e)}")

                # Import des donnees dans PostgreSQL-PostGIS
                print("self.SHP =", self.SHP)
                self.log_to_console(f"self.SHP = {self.SHP}")
                print(f"glob.glob(self.SHP) = {glob.glob(self.SHP)}")
                self.log_to_console(f"glob.glob(self.SHP) = {glob.glob(self.SHP)}")
                for layer in shp_files:
                    try:
                        self.log_to_console(f"[INFO] importing layer {layer}")
                        self.upload_to_db(layer, database)
                        self.log_to_console(f"[INFO] layer imported succesfuly ({layer})")
                        self.report["logs"].append(f"Import réussi : {layer}")
                    except Exception as e:
                        self.report["shp_files_errors"] += 1
                        self.log_to_console(f"[INFO] Error importing layer {layer}: {str(e)}")
                        self.report["logs"].append(f"Erreur d'import sur {layer} : {str(e)}")

                conn = psycopg2.connect(
                    host=database["host"],
                    dbname=database["dbname"],
                    user=database["user"],
                    password=database["password"],
                    port=database["port"]
                )

                sql = """
                INSERT INTO {}.basedoc(
                    id_source,
                    depco,
                    no_origine,
                    aep,
                    eu,
                    epl,
                    localisat,
                    type_plan,
                    b_etude,
                    entreprise,
                    date,
                    echelle,
                    cote,
                    etat,
                    q_support,
                    nom_fich,
                    utilisat)
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                );""".format(psycopg2.extensions.quote_ident(database["schema"], conn))
                
                values = (
                    id_source, depco, no_origine, aep, eu, epl, localisat, 
                    type_plan, b_etude, str(entreprise), date_str, echelle, 
                    cote, etat, q_support, nom_fichier, utilisat
                )
                
                cursor = conn.cursor()
                cursor.execute(sql, values)
                self.log_to_console(f"[INFO] executing sql request")
                self.log_to_console(f"[INFO] commiting changes")
                conn.commit()
                cursor.close()
                self.log_to_console(f"[INFO] cursor closed")
                conn.close()
                self.log_to_console(f"[INFO] Insertion réussie dans la base.")
                QMessageBox.information(self, "Succès", f"Insertion réussie dans la base !")
                self.show_report_popup()

            except Exception as e:
                print(traceback.format_exc())
                self.log_to_console(f"[ERROR] Erreur lors de l'insertion :{e}")
                # QMessageBox.critical(self, "Erreur", f"Erreur lors de l'insertion :\n{e}")
                MessagesBoxes.error(self, "Erreur", f"Erreur lors de l'insertion :\n{e}",
                                    savelog=True,
                                    console_logs=self.console_textedit.toPlainText(), folder=self.FOLDER)
        else:
            self.report = {
                "total_layers": 50,
                "added_layers": 40,
                "modified_layers": 0,
                "shp_files_processed": 50,
                "shp_files_errors": 5,
                "shp_files_ignored": 5,
                "logs": []
            }
            self.log_to_console(f"[INFO] Insertion réussie dans la base.")
            QMessageBox.information(self, "Succès", f"Insertion réussie dans la base !")
            self.show_report_popup()

    def run_deployment(self):
        global db_consultation, db_work

        self.add_console_tab()
        self.log_to_console("[INFO] run_deployment called")
        if not is_test_mode:
            
            groupes = self.get_groupes()
            if not groupes:
                MessagesBoxes.error(self,"Error", "Aucun groupes n'a été trouvé. Abandon.", savelog=True, console_logs=self.console_textedit.toPlainText())
                return

            # Création de la popup
            popup = QDialog(self)
            popup.setWindowTitle("Sélectionner un groupe")
            layout = QVBoxLayout(popup)

            combo = QComboBox(popup)
            combo.addItems(groupes)
            layout.addWidget(QLabel("Sélectionnez le groupe d'utilisateurs de consultation :"))
            layout.addWidget(combo)
            button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=popup)
            layout.addWidget(button_box)

            button_box.accepted.connect(popup.accept)
            button_box.rejected.connect(popup.reject)

            self.log_to_console("[INFO] affichage de la popup de groupe et en attente de la réponse de l'utilisateur")
            if popup.exec_() == QDialog.Accepted:
                selected_group = combo.currentText()
                group = selected_group
                self.log_to_console("[INFO] Réponse : OK. Group: group")
            else:
                self.log_to_console("[INFO] Réponse : Canceled. Aborting")
                self.tabs.removeTab(4)
                return
            databases = ['db_consultation', 'db_work']
            for db in databases:
                if db == "db_consultation":
                    dbname = self.db_consultation_combo.currentText()
                elif db == 'db_work':
                    dbname = self.db_work_combo.currentText()
                else:
                    raise Exception(f"The selected database {db} is not defined")
                self.log_to_console(f"[INFO] base de données : {dbname}")
                settings = QgsSettings()
                settings.beginGroup(f"PostgreSQL/connections/{dbname}")
                db_dict = {
                    "host": settings.value("host", ""),
                    "port": settings.value("port", ""),
                    "dbname": settings.value("database", ""),
                    "user": settings.value("username", ""),
                    "password": settings.value("password", ""),
                    "schema": settings.value("schema", "")
                }

                safe_db_dict = db_dict.copy()
                safe_db_dict["password"] = "[PASSWORD HIDDEN FOR SECURITY REASONS]"

                self.log_to_console(f"[INFO] Dictionnaire des informations relatives à la base de données : {safe_db_dict}")

                settings.endGroup()

                if db == "db_consultation":
                    db_consultation = db_dict
                    try:
                        schemas = get_shamas(db_consultation["host"], db_consultation["port"], db_consultation["dbname"],
                                            self.db_username.text(),
                                            self.db_password.text())
                    except Exception as e:
                        if "authentication failed" in str(e).lower():
                            self.log_to_console("[WARNING] Authentification failed")
                            QMessageBox.critical(self, "Erreur d'authentification", 
                                                  "Échec de l'authentification.\nVeuillez vérifier votre nom d'utilisateur et votre mot de passe.")
                            self.run_deployment()
                            return
                        else:
                            self.log_to_console(f"[ERROR] Error getting schemas: {e}")
                            MessagesBoxes.error(self, "Erreur de connexion", 
                                                f"Impossible de se connecter à la base de données. Erreur: {e}",savelog=True,console_logs=self.console_textedit.toPlainText(), folder=self.FOLDER)
                            return
                    schemas.sort()
                    self.log_to_console(f"[INFO] Schémas disponibles : {schemas}")
                    self.log_to_console(f"[INFO] Affichage de la popup de sélection du schéma")
                    schema, ok = QInputDialog.getItem(self, "Schema",
                                                    "Veuillez sélectionner le schéma désiré pour la base de données de consultation (celui-ci sera supprimé, puis recréé avec les nouvelles données) :",
                                                    schemas, 0, False)

                    self.log_to_console(f"[INFO] Popup affichée. En attente de la réponse de l'utilisateur")
                    if ok and schema:

                        self.log_to_console(f"[INFO] L'utilisateur a sélectionné '{schema}' ")
                        db_consultation["schema"] = schema
                    else:
                        self.log_to_console(f"[WARNING] L'utilisateur n'a rien selectionné. Aborting.")
                        return
                else:
                    db_work = db_dict
                    try:
                        schemas = get_shamas(db_work["host"], db_work["port"], db_work["dbname"],
                                        self.db_username.text(),
                                        self.db_password.text())
                    except Exception as e:
                        if "authentication failed" in str(e).lower():
                            self.log_to_console("[WARNING] Authentification failed")
                            QMessageBox.critical(self, "Erreur d'authentification", 
                                                  "Échec de l'authentification.\nVeuillez vérifier votre nom d'utilisateur et votre mot de passe.")
                            self.run_deployment()
                            return
                        else:
                            self.log_to_console(f"[ERROR] Error getting schemas: {e}")
                            MessagesBoxes.error(self, "Erreur de connexion", 
                                                f"Impossible de se connecter à la base de données. Erreur: {e}",savelog=True,console_logs=self.console_textedit.toPlainText(), folder=self.FOLDER)
                            return
                    schemas.sort()
                    self.log_to_console(f"[INFO] Schémas disponibles : {schemas}")
                    self.log_to_console(f"[INFO] Affichage de la popup de sélection du schéma")
                    schema, ok = QInputDialog.getItem(self, "Schema",
                                                    "Veuillez sélectionner le schéma désiré pour la base de données de travail :",
                                                    schemas, 0, False)
                    self.log_to_console(f"[INFO] Popup affichée. En attente de la réponse de l'utilisateur")
                    if ok and schema:
                        self.log_to_console(f"[INFO] L'utilisateur a selectionné '{schema}' ")
                        db_work["schema"] = schema
                    else:
                        self.log_to_console(f"[WARNING] L'utilisateur n'a rien sélectionné. Aborting.")
                        self.tabs.removeTab(4)
                        return

            db_consultation_backup_path = self.backup_consultation_path
            password = self.db_password.text()
            username = self.db_username.text()
            backup_travail_path = self.backup_travail_path
            message = (
                f"[INFO] Rapport des données avant le lancement :\n"
                f"* db_consultation_backup_path : {db_consultation_backup_path}\n"
                f"* password : {password}\n"
                f"* username : {username}\n"
                f"* backup_travail_path : {backup_travail_path}")
            message = message.replace(
                f"* password : {password}",
                "* password : [PASSWORD HIDDEN FOR SECURITY REASONS]"
            )
            self.log_to_console(message)
            batch_content = f"""
            @echo off
            set PGPASSWORD={password}
            pg_dump.exe -h {db_consultation['host']} -U {username} -d {db_consultation['dbname']} -p {db_consultation['port']} -n {db_consultation['schema']} -E UTF8 > "{db_consultation_backup_path}\\{db_consultation['schema']}_backup.sql"
            pg_dump.exe -h {db_work['host']} -U {username} -d {db_work['dbname']} -p {db_work['port']} -n {db_work['schema']} -E UTF8 > "{backup_travail_path}\\{db_work['schema']}.sql"
            """
            safe_batch_content = batch_content.replace(
                f"set PGPASSWORD={password}",
                "set PGPASSWORD=[PASSWORD HIDDEN FOR SECURITY REASONS]"
            )

            self.log_to_console(f"[INFO] Contenu du fichier batch : {safe_batch_content}")
            self.log_to_console(f"[INFO] Création du fichier batch temporaire")
            print(batch_content)
            batch_content = '\n'.join([line.strip() for line in batch_content.split('\n') if line.strip()])
            with tempfile.NamedTemporaryFile(suffix='.bat', delete=False, mode='w') as f:
                f.write(batch_content)
                bat_path = f.name
            self.log_to_console(f"[INFO] Fichier batch temporaire créé. bat_path : {bat_path}")
            try:
                result = subprocess.run(
                    [bat_path],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='cp1252'  # ou encoding='mbcs' mais en théorie c'est encoding='cp1252'. à voir si nous devons changer ça dans le futur
                )
            except subprocess.CalledProcessError as e:
                # QMessageBox.critical(self, "Erreur",
                #                         f"Sortie standard : {e.stdout}\nErreur standard : {e.stderr}")
                MessagesBoxes.error(self, "Erreur", f"Sortie standard : {e.stdout}\nErreur standard : {e.stderr}",
                                    savelog=True,
                                    console_logs=self.console_textedit.toPlainText(), folder=self.save_dir_path)
                self.log_to_console(f"[ERROR] Erreur lors de l'exécution du batch : Sortie standard : {e.stdout}\nErreur standard : {e.stderr}")
                print("Erreur lors de l'exécution du batch :")
                print("Sortie standard :", e.stdout)
                print("Erreur standard :", e.stderr)

            finally:
                self.log_to_console(
                    f"[INFO] Supression du batch temporaire")
                try:
                    os.unlink(bat_path)

                    self.log_to_console(
                        f"[INFO] Supression terminée")
                except:
                    pass
            try:
                batch_content = f"""
                @echo off
                set PGPASSWORD={password}
                psql.exe -h {db_consultation['host']} -U {username} -d {db_consultation['dbname']} -p {db_consultation['port']} < "{backup_travail_path}\\{db_consultation['schema']}.sql"
                """
                conn = psycopg2.connect(
                    host=db_consultation["host"],
                    dbname=db_consultation["dbname"],
                    user=username,
                    port=db_consultation["port"],
                    password=password
                )
                cur = conn.cursor()
                cur.execute(f"DROP SCHEMA IF EXISTS {db_consultation['schema']} CASCADE;")
                conn.commit()
                batch_content = '\n'.join([line.strip() for line in batch_content.split('\n') if line.strip()])
                with tempfile.NamedTemporaryFile(suffix='.bat', delete=False, mode='w') as f:
                    f.write(batch_content)
                    bat_path = f.name
                safe_batch_content = batch_content.replace(
                    f"set PGPASSWORD={password}",
                    "set PGPASSWORD=[PASSWORD HIDDEN FOR SECURITY REASONS]"
                )

                self.log_to_console(f"[INFO] Contenu du fichier batch : {safe_batch_content}")
                self.log_to_console(f"[INFO] Fichier batch temporaire créé. bat_path : {bat_path}")
                try:
                    result = subprocess.run(
                        [bat_path],
                        check=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='cp1252'
                        # ou encoding='mbcs' mais en théorie c'est encoding='cp1252'. à voir si nous devons changer ça dans le futur
                    )
                except subprocess.CalledProcessError as e:
                #     QMessageBox.critical(self, "Erreur",
                #                          f"Sortie standard : {e.stdout}\nErreur standard : {e.stderr}")
                    MessagesBoxes.error(self, "Erreur", f"Sortie standard : {e.stdout}\nErreur standard : {e.stderr}", savelog=True,
                                        console_logs=self.console_textedit.toPlainText())
                    self.log_to_console(
                        f"[ERROR] Erreur lors de l'exécution du batch : Sortie standard : {e.stdout}\nErreur standard : {e.stderr}")
                    print("Erreur lors de l'exécution du batch :")
                    print("Sortie standard :", e.stdout)
                    print("Erreur standard :", e.stderr)

                finally:
                    self.log_to_console(
                        f"[INFO] Suppression du batch temporaire")
                    try:
                        os.unlink(bat_path)

                        self.log_to_console(
                            f"[INFO] Suppression terminée")
                    except:
                        pass
                command2 = f"GRANT USAGE ON SCHEMA {db_consultation['schema']} TO {group};"
                command3 = f"ALTER DEFAULT PRIVILEGES IN SCHEMA {db_consultation['schema']} GRANT SELECT ON TABLES TO {group};"
                self.log_to_console(f"[INFO] Executing command2 : {command2}")
                cur.execute(command2)
                self.log_to_console(f"[INFO] Succes.")
                self.log_to_console(f"[INFO] Executing command3 : {command3}")
                cur.execute(command3)
                self.log_to_console(f"[INFO] Succes.")
                conn.commit()
                self.log_to_console(f"[INFO] Changes commited.")
                cur.close()
                self.log_to_console(f"[INFO] Cursor closed.")
                conn.close()
                self.log_to_console(f"[INFO] Connection closed.")
            except Exception as e:
                MessagesBoxes.error(self, "Erreur", f"Erreur lors du déploiement : {e}", savelog=True,
                                    console_logs=self.console_textedit.toPlainText(), folder=self.save_dir_path)
            finally:
                MessagesBoxes.succes(self, "Information", "Déploiement terminé.", savelog=True, console_logs=self.console_textedit.toPlainText(), folder=self.save_dir_path)
        else:
            self.log_to_console(f"[INFO] Connection closed.")
            MessagesBoxes.succes(self, "Information", "Déploiement terminé.", savelog=True, console_logs=self.console_textedit.toPlainText(), folder=self.save_dir_path)
        # continuer la boucle de manière dégueu, mais bon faute de meilleur idée...
        # le but est de ne pas terminer le processus, on attends un certain nombre de secondes pour après fermer l'onglet console. Cela dis, ça ne sera pas super fluide, étant donné que l'interface sera mise à jour toute les 0.1 secondes.
        for item in range(1000):
            time.sleep(0.1)
            QCoreApplication.processEvents()

        self.tabs.removeTab(4)
