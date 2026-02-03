import os
import zipfile
import tempfile
import logging
from datetime import datetime
from qgis.PyQt.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, 
                                QCheckBox, QDialogButtonBox, QLabel)
from qgis.PyQt.QtCore import QSettings

logger = logging.getLogger('DourBase')


def select_export_categories(parent_widget=None):
    """
    Affiche une boîte de dialogue pour sélectionner les catégories à exporter
    Retourne un dictionnaire des catégories sélectionnées ou None si annulé
    """
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Sélection des catégories d'export")
    dialog.setMinimumWidth(400)

    layout = QVBoxLayout(dialog)

    info_label = QLabel("Sélectionnez les catégories de données à exporter :")
    info_label.setWordWrap(True)
    layout.addWidget(info_label)

    categories = {
        'logs': ("Logs du plugin", "Inclure les fichiers de logs du plugin"),
        'config': ("Configuration", "Inclure les paramètres de configuration actuels"),
        'metadata': ("Métadonnées", "Inclure les métadonnées du plugin"),
        'build_info': ("Informations de build", "Inclure les informations de compilation")
    }
    
    checkboxes = {}
    for key, (title, tooltip) in categories.items():
        checkbox = QCheckBox(title)
        checkbox.setToolTip(tooltip)
        checkbox.setChecked(True)
        layout.addWidget(checkbox)
        checkboxes[key] = checkbox

    button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
    button_box.accepted.connect(dialog.accept)
    button_box.rejected.connect(dialog.reject)
    layout.addWidget(button_box)

    if dialog.exec_() == QDialog.Accepted:
        return {
            'logs': checkboxes['logs'].isChecked(),
            'config': checkboxes['config'].isChecked(),
            'metadata': checkboxes['metadata'].isChecked(),
            'build_info': checkboxes['build_info'].isChecked()
        }
    return None


def export_plugin_data(parent_widget=None):
    """
    Exporte les données du plugin dans un fichier ZIP en fonction des catégories sélectionnées
    Retourne le chemin du fichier ZIP créé ou None en cas d'erreur
    """
    categories = select_export_categories(parent_widget)
    if not categories:
        logger.info("Export annulé par l'utilisateur")
        return None

    if not any(categories.values()):
        QMessageBox.warning(
            parent_widget,
            "Aucune catégorie sélectionnée",
            "Veuillez sélectionner au moins une catégorie à exporter."
        )
        return export_plugin_data(parent_widget)

    msg_box = QMessageBox(parent_widget)
    msg_box.setIcon(QMessageBox.Information)
    msg_box.setWindowTitle("Confirmation avant collecte des données")
    msg_box.setText("Export des données du plugin")

    selected_categories = []
    details = []

    if categories['logs']:
        selected_categories.append("les logs du plugin")
        details.append("- Le nom de la base de données")
        details.append("- L'identifiant de la base de données")
        details.append("- L'adresse IP du serveur PostgreSQL")
    if categories['config']:
        selected_categories.append("les paramètres de configuration")
        details.append("- Le chemin des fichiers de configuration CSV s'il est personnalisé")
    if categories['metadata']:
        selected_categories.append("les métadonnées du plugin")
    if categories['build_info']:
        selected_categories.append("les informations de build")

    if len(selected_categories) == 1:
        categories_text = selected_categories[0]
    elif len(selected_categories) == 2:
        categories_text = " et ".join(selected_categories)
    else:
        categories_text = ", ".join(selected_categories[:-1]) + " et " + selected_categories[-1]

    message = f"Vous allez générer un fichier ZIP contenant {categories_text}."

    if details:
        message += "\n\nCe fichier peut exposer des données sensibles selon le contexte :\n" + "\n".join(details)

    if categories['logs']:
        message += "\n\nNote : Les mots de passe ne sont pas inclus dans ce ZIP."

    message += "\n\nDemandez l'accord d'un administrateur système si nécessaire avant de procéder."

    msg_box.setInformativeText(message)
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

            if categories.get('logs', False):
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

            if categories.get('build_info', False):
                build_info_path = os.path.join(plugin_dir, 'build_infos.txt')
                if os.path.exists(build_info_path):
                    zipf.write(build_info_path, 'build_infos.txt')
                    logger.debug("Fichier build_infos.txt ajouté à l'export")

            if categories.get('metadata', False):
                metadata_path = os.path.join(plugin_dir, 'metadata.txt')
                if os.path.exists(metadata_path):
                    zipf.write(metadata_path, 'metadata.txt')
                    logger.debug("Fichier metadata.txt ajouté à l'export")

            if categories.get('config', False):
                s = QSettings()
                configs = {}
                s.beginGroup("DourBase")
                for key in s.childKeys():
                    if 'password' not in key.lower() and 'token' not in key.lower():
                        configs[key] = s.value(key)
                s.endGroup()
                logger.debug(f"{len(configs)} paramètres de configuration récupérés")

                if configs:
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
