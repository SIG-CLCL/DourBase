import csv
import os
import logging
import logging.handlers
from qgis.PyQt.QtCore import QSettings
import os
import csv
from qgis.core import QgsDataSourceUri
from qgis.PyQt.QtSql import QSqlDatabase, QSqlQuery
import shutil

def get_plugin_version():
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "metadata.txt"), "r") as f:
        for line in f:
            if line.startswith("version="):
                return line.split("=")[1].strip()
    return "Unknown"
def setup_logging():
    """Configure la gestion des logs avec rotation et taille maximale"""
    logger = logging.getLogger('DourBase')
    logger.setLevel(logging.DEBUG)
    
    # Créer le dossier de logs s'il n'existe pas
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'dourbase.log')
    
    # Configuration via QSettings
    s = QSettings()
    # Taille max d'un fichier de log en Mo (défaut: 5 Mo)
    log_max_size_mb = int(s.value("DourBase/log_max_size_mb", 5))
    # Nombre de fichiers de backup à conserver (défaut: 5)
    log_backup_count = int(s.value("DourBase/log_backup_count", 5))
    
    # Configuration du handler avec rotation
    handler = logging.handlers.RotatingFileHandler(
        log_file, 
        maxBytes=log_max_size_mb * 1024 * 1024,  # Convertir en octets
        backupCount=log_backup_count,
        encoding='utf-8'
    )
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    
    # Vider les handlers existants pour éviter les doublons
    if logger.hasHandlers():
        logger.handlers.clear()
    
    logger.addHandler(handler)
    logger.info("Logging initialisé avec succès")
    return logger

# Initialisation du logger
logger = setup_logging()
logger = logging.getLogger('DourBase')

def get_config_dir():
    logger.info("[utils] [get_config_dir] Getting configuration directory path")
    s = QSettings()
    if s.value("DourBase/csv_dir", "%INTERNAL%") == "%INTERNAL%":
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
        logger.info(f"[utils] [get_config_dir] Using internal config directory: {path}")
    else:
        path = s.value("DourBase/csv_dir", "%INTERNAL%")
        logger.info(f"[utils] [get_config_dir] Using custom config directory: {path}")
    return path
def get_param(param_name):
    logger.info(f"[utils] [get_param] Getting parameter: {param_name}")
    s = QSettings()
    value = s.value(f"DourBase/{param_name}")
    logger.info(f"[utils] [get_param] Parameter value: {value}")
    return value

def update_file_name(depco, num_source, aep=False, eu=False, epl=False):
    logger.info(f"[utils] [update_file_name] Generating file name - depco: {depco}, num_source: {num_source}, aep: {aep}, eu: {eu}, epl: {epl}")
    if not aep and not eu and not epl:
        logger.error("[utils] [update_file_name] No file type specified (aep/eu/epl)")
        raise ValueError("At least one argument (aep/eu/epl) should be True.")
    name = f'{depco}'
    if aep:
        name = f"{name}_AEP"
    if eu:
        name = f"{name}_EU"
    if epl:
        name += f"{name}_EPL"
    name += "_" + num_source
    result = name.upper()
    logger.info(f"[utils] [update_file_name] Generated file name: {result}")
    return result

def open_config(filename, dir=None):
    logger.info(f"[utils] [open_config] Opening config file: {filename}, directory: {dir if dir else 'None'}")
    s = QSettings()
    if dir:
        if dir == "config":
            if s.value("DourBase/csv_dir", "%INTERNAL%") == "%INTERNAL%":
                path = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    dir if dir else '',
                    filename
                )
            else:
                path = os.path.join(s.value("DourBase/csv_dir", "%INTERNAL%"), filename)
        else:
            path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                dir if dir else '',
                filename
            )
    else:
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            dir if dir else '',
            filename
        )

    logger.info(f"[utils] [open_config] filename is : {filename}, dir : {dir}, path : {path}")
    tmp_list = []
    try:
        logger.info(f"[utils] [open_config] Reading file: {path}")
        with open(path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter=';')
            row_count = 0
            for row in reader:
                if len(row) >= 2:
                    try:
                        tmp_list.append((row[1], int(row[0])))
                        row_count += 1
                    except ValueError as e:
                        logger.warning(f"[utils] [open_config] Error converting value in row: {e}")
                        tmp_list.append((f"Error : {e}", "ERROR"))
            logger.info(f"[utils] [open_config] Successfully read {row_count} rows from {filename}")
    except FileNotFoundError:
        logger.error(f"[utils] [open_config] Config file not found: {path}")
        raise
    except Exception as e:
        logger.error(f"[utils] [open_config] Error reading config file: {str(e)}", exc_info=True)
        raise
    return tmp_list

def check_shapefile_completeness(folder):
    logger.info(f"[utils] [check_shapefile_completeness] Checking shapefile completeness in: {folder}")
    required_exts = {'.shp', '.shx', '.dbf', '.prj'}
    all_files = os.listdir(folder)
    shapefile_basenames = set(os.path.splitext(f)[0] for f in all_files if f.endswith('.shp'))
    logger.debug(f"[utils] [check_shapefile_completeness] Found {len(shapefile_basenames)} shapefile(s)")
    missing_files_list = []

    for basename in shapefile_basenames:
        logger.debug(f"[utils] [check_shapefile_completeness] Checking shapefile: {basename}")
        present_exts = {os.path.splitext(f)[1] for f in all_files if os.path.splitext(f)[0] == basename}
        missing_exts = required_exts - present_exts
        for ext in missing_exts:
            missing_files_list.append(f"{basename}{ext}")
            logger.warning(f"[utils] [check_shapefile_completeness] Missing extension: {ext}")

    if missing_files_list:
        if len(missing_files_list) == 1:
            error_message = "Un fichier est manquant :\n" + missing_files_list[0]
        else:
            error_message = "Des fichiers sont manquants :\n" + "\n".join(missing_files_list)
        logger.error(error_message)
        raise FileNotFoundError(error_message)
    else:
        logger.info("[utils] [check_shapefile_completeness] All required shapefile components are present")
        return list(shapefile_basenames)

def get_filename_without_extension(filepath):
    """
    Récupère le nom du fichier sans extension à partir d'un chemin complet.
    """
    logger.info(f"[utils] [get_filename_without_extension] Getting filename without extension from: {filepath}")
    basename = os.path.basename(filepath)
    filename, _ = os.path.splitext(basename)
    logger.info(f"[utils] [get_filename_without_extension] Filename without extension: {filename}")
    return filename

def get_suffix_after_last_underscore(filepath):
    """
    Récupère la partie après le dernier underscore du nom de fichier (sans extension du coup).
    """
    logger.info(f"[utils] [get_suffix_after_last_underscore] Getting suffix after last underscore from: {filepath}")
    filename = get_filename_without_extension(filepath)
    suffix = filename.split('_')[-1]
    logger.info(f"[utils] [get_suffix_after_last_underscore] Suffix after last underscore: {suffix}")
    return suffix

def get_shamas(host, port, database_name, username, password):

    # Define the database connection parameters
    uri = QgsDataSourceUri()
    uri.setConnection(host, port, database_name, username, password)

    # Open a connection to the database
    db = QSqlDatabase.addDatabase("QPSQL")  # (QPSQL for PostgreSQL)
    db.setHostName(uri.host())
    db.setPort(int(uri.port()))
    db.setDatabaseName(uri.database())
    db.setUserName(uri.username())
    db.setPassword(uri.password())

    if db.open():
        logger.info("[utils] [get_shamas] Database connection successful!")

        query = QSqlQuery(db)
        query.exec_("SELECT schema_name FROM information_schema.schemata")

        schemas = []
        while query.next():
            schemas.append(query.value(0))
        logger.info(f"[utils] [get_shamas] Schemas : {schemas}")
        db.close()
        return schemas
    else:
        logger.error(f"[utils] [get_shamas] Failed to connect to the database: {db.lastError().text()}")
        db.close()
        raise Exception(db.lastError().text())

def read_shp_types(filepath):
    with open(filepath, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def prepare_convert_folder(blank_dir, convert_dir):
    os.makedirs(convert_dir, exist_ok=True)
    for item in os.listdir(convert_dir):
        if item.lower() != "readme.md":
            path = os.path.join(convert_dir, item)
            if os.path.isfile(path) or os.path.islink(path):
                os.remove(path)
            elif os.path.isdir(path):
                shutil.rmtree(path)
    for item in os.listdir(blank_dir):
        s = os.path.join(blank_dir, item)
        d = os.path.join(convert_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)

def copy_actual_shp_files(src_folder, convert_dir):
    for file in os.listdir(src_folder):
        if file.lower().endswith(('.shp', '.shx', '.dbf', '.prj')):
            shutil.copy2(os.path.join(src_folder, file), os.path.join(convert_dir, file))

def main_prepare_shapefiles(user_shp_folder):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    blank_dir = os.path.join(base_dir, "SHPS", "blank")
    convert_dir = os.path.join(base_dir, "SHPS", "convert")

    # 1. Reset convert
    prepare_convert_folder(blank_dir, convert_dir)
    # 2. Copier les fichiers réels de l'utilisateur
    copy_actual_shp_files(user_shp_folder, convert_dir)
    return convert_dir
