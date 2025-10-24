import os
import zipfile
import tempfile
import json
import logging
from datetime import datetime
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSettings

logger = logging.getLogger('DourBase')

def export_plugin_data(parent_widget=None):
    """
    Exporte les données du plugin (logs, build infos, configs) dans un fichier ZIP
    Retourne le chemin du fichier ZIP créé ou None en cas d'erreur
    """
    msg_box = QMessageBox(parent_widget)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("Confirmation avant collecte des logs")
    msg_box.setText("Export des données du plugin")
    msg_box.setInformativeText(
        "Vous allez générer un fichier ZIP contenant les logs du plugin, les informations "
        "de build et les paramètres actuels.\n\n"
        "Ce fichier peut exposer des données sensibles selon le contexte :\n"
        "- Le chemin des fichiers de configuration CSV s'il est personnalisé\n"
        "- Le nom de la base de données\n"
        "- L'identifiant de la base de données\n"
        "- L'adresse IP du serveur PostgreSQL\n\n"
        "Note : Les mots de passe ne sont pas inclus dans ce ZIP.\n\n"
        "Demandez l'accord d'un administrateur système si nécessaire avant de procéder."
    )
    msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
    msg_box.setDefaultButton(QMessageBox.Cancel)
    
    if msg_box.exec_() != QMessageBox.Ok:
        logger.info("Export annulé par l'utilisateur")
        return None

    try:
        temp_dir = tempfile.mkdtemp()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_path = os.path.join(temp_dir, f"dourbase_export_{timestamp}.zip")
        logger.debug(f"Création du fichier d'export temporaire: {zip_path}")
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            logs_dir = os.path.join(plugin_dir, 'logs')
            
            if os.path.exists(logs_dir):
                logger.debug(f"Export des logs depuis: {logs_dir}")
                for item in os.listdir(logs_dir):
                    src_path = os.path.join(logs_dir, item)
                    if os.path.isfile(src_path):
                        rel_path = os.path.join('logs', os.path.basename(item))
                        zipf.write(src_path, rel_path)
                    elif os.path.isdir(src_path):
                        for root, _, files in os.walk(src_path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                rel_path = os.path.join('logs', os.path.basename(src_path), file)
                                zipf.write(file_path, rel_path)
            
            plugin_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            build_info_path = os.path.join(plugin_dir, 'build_infos.txt')
            if os.path.exists(build_info_path):
                zipf.write(build_info_path, 'build_infos.txt')
                logger.debug("Fichier build_infos.txt ajouté à l'export")
                
            metadata_path = os.path.join(plugin_dir, 'metadata.txt')
            if os.path.exists(metadata_path):
                zipf.write(metadata_path, 'metadata.txt')
                logger.debug("Fichier metadata.txt ajouté à l'export")
            
            s = QSettings()
            
            configs = {}
            s.beginGroup("DourBase")
            for key in s.childKeys():
                configs[key] = s.value(key)
            s.endGroup()
            logger.debug(f"{len(configs)} paramètres de configuration récupérés")
            
            configs_path = os.path.join(temp_dir, 'configs.txt')
            with open(configs_path, 'w', encoding='utf-8') as f:
                f.write("=== PARAMÈTRES DU PLUGIN ===\n\n")
                for key, value in sorted(configs.items()):
                    f.write(f"{key} = {value}\n")
            
            zipf.write(configs_path, 'configs.txt')
            os.remove(configs_path)
        
        logger.info(f"Export terminé avec succès: {zip_path}")
        return zip_path
        
    except Exception as e:
        QMessageBox.critical(
            parent_widget,
            "Erreur lors de l'export",
            f"Une erreur est survenue lors de l'export des données :\n{str(e)}"
        )
        return None
