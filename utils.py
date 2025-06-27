import csv
import os
import logging
import shutil
from qgis.core import QgsDataSourceUri
from qgis.PyQt.QtCore import QSettings
from PyQt5.QtSql import QSqlDatabase, QSqlQuery

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')

if not os.path.exists(log_dir):
    os.makedirs(log_dir)

logging.basicConfig(
    filename=os.path.join(log_dir, 'plugin.log'),
    level=logging.INFO,  # Niveau de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def update_file_name(depco, num_source, aep=False, eu=False, epl=False):
    if not aep and not eu and not epl:
        raise ValueError("At least one argument (aep/eu/epl) should be True.")
    name = f'{depco}'
    if aep:
        name = f"{name}_AEP"
    if eu:
        name = f"{name}_EU"
    if epl:
        name += f"{name}_EPL"
    name += "_" + num_source
    return name.upper()

def open_config(filename, dir=None):
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

    logging.info(f"[utils] [open_config] filename is : {filename}, dir : {dir}, path : {path}")
    tmp_list = []
    try:
        with open(path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file, delimiter=';')
            for row in reader:
                if len(row) >= 2:
                    try:
                        tmp_list.append((row[1], int(row[0])))
                    except ValueError as e:
                        tmp_list.append((f"Error : {e}", "ERROR"))
    except Exception as e:
        print(f"[ERROR] [open_config] : {e}")
    return tmp_list

def check_shapefile_completeness(folder):
    required_exts = {'.shp', '.shx', '.dbf', '.prj'}
    all_files = os.listdir(folder)
    shapefile_basenames = set(os.path.splitext(f)[0] for f in all_files if f.endswith('.shp'))
    missing_files_list = []

    for basename in shapefile_basenames:
        present_exts = {os.path.splitext(f)[1] for f in all_files if os.path.splitext(f)[0] == basename}
        missing_exts = required_exts - present_exts
        for ext in missing_exts:
            missing_files_list.append(f"{basename}{ext}")

    if missing_files_list:
        if len(missing_files_list) == 1:
            error_message = "Un fichier est manquant :\n" + missing_files_list[0]
        else:
            error_message = "Des fichiers sont manquants :\n" + "\n".join(missing_files_list)
        raise FileNotFoundError(error_message)
    else:
        return list(shapefile_basenames)


def get_filename_without_extension(filepath):
    """
    Récupère le nom du fichier sans extension à partir d'un chemin complet.
    """
    basename = os.path.basename(filepath)
    filename, _ = os.path.splitext(basename)
    return filename

def get_suffix_after_last_underscore(filepath):
    """
    Récupère la partie après le dernier underscore du nom de fichier (sans extension du coup).
    """
    filename = get_filename_without_extension(filepath)
    suffix = filename.split('_')[-1]
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
        logging.info("Database connection successful!")

        query = QSqlQuery(db)
        query.exec_("SELECT schema_name FROM information_schema.schemata")

        schemas = []
        while query.next():
            schemas.append(query.value(0))
        print(f"Schemas : {schemas}")
        logging.info(f"Schemas : {schemas}")
        db.close()
        return schemas
    else:
        logging.error("Failed to connect to the database:", db.lastError().text())
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
