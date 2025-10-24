import os
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Tuple

# Set up logger
logger = logging.getLogger('DourBase')

REQUIRED_FILES = {
    "DEPCO.csv",
    "ENTREPRISE.csv",
    "ETAT.csv",
    "EXPLOITANT.csv",
    "MOA.csv",
    "Q_SUPPORT.csv"
}

class CSVCheckerError(Exception):
    """Exception personnalisée pour les erreurs du CSVChecker."""
    pass

class CSVChecker:
    """
    Vérificateur de fichiers CSV pour DourBase.
    
    Cette classe permet de vérifier la présence et l'intégrité des fichiers CSV
    nécessaires au bon fonctionnement de l'application.
    
    Args:
        directory (str): Chemin vers le dossier contenant les fichiers CSV
    """
    
    def __init__(self, directory: str):
        """Initialise le vérificateur avec le répertoire à vérifier."""
        self.directory = Path(directory)
        logger.info(f"Initializing CSVChecker for directory: {self.directory}")
        self._reset_state()
    
    def _reset_state(self) -> None:
        """Réinitialise l'état du vérificateur."""
        self.problems: List[str] = []
        self.missing_files: List[str] = []
        self.checked_files: Set[str] = set()
        self._valid_files: Set[str] = set()
    
    def check_files_exist(self) -> bool:
        """
        Vérifie la présence des fichiers requis.
        
        Returns:
            bool: True si tous les fichiers requis sont présents, False sinon
        """
        logger.debug(f"Checking for required files in: {self.directory}")
        try:
            existing_files = {f.name for f in self.directory.glob("*.csv")}
            self.missing_files = sorted(REQUIRED_FILES - existing_files)
            
            if self.missing_files:
                logger.warning(f"Missing required files: {', '.join(self.missing_files)}")
                for file in self.missing_files:
                    problem_msg = f"Missing file: {file}"
                    self.problems.append(problem_msg)
            else:
                logger.debug("All required CSV files are present")
                
            return len(self.missing_files) == 0
        except Exception as e:
            error_msg = f"Error while checking files: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise CSVCheckerError(error_msg) from e

    def _validate_depco_content(self, reader) -> List[str]:
        """Valide le contenu spécifique du fichier DEPCO.csv."""
        problems = []
        seen_codes = set()
        logger.debug("Validating DEPCO.csv content")
        for row_num, row in enumerate(reader, 1):
            if len(row) < 2:
                problems.append(f"Ligne {row_num} : Format invalide, attendu 'code;libellé'")
                continue
                
            code, libelle = row[0].strip(), row[1].strip()
            if not code:
                problems.append(f"Ligne {row_num} : Code manquant")
            elif code in seen_codes:
                problems.append(f"Ligne {row_num} : Code en double : {code}")
            else:
                seen_codes.add(code)
                try:
                    code_num = int(code)
                    if code_num < 0:
                        problems.append(f"Ligne {row_num} : Code négatif non autorisé : {code}")
                except ValueError:
                    problems.append(f"Ligne {row_num} : Code invalide (doit être un nombre) : {code}")
            if not libelle:
                problems.append(f"Ligne {row_num} : Libellé manquant pour le code {code}")
        return problems

    def _read_csv_file(self, filepath: Path) -> Tuple[List[List[str]], List[str]]:
        """
        Lit un fichier CSV et retourne ses lignes et les problèmes éventuels.
        Les lignes vides sont automatiquement ignorées.
        
        Args:
            filepath: Chemin vers le fichier CSV
            
        Returns:
            Tuple contenant :
            - Liste des lignes non vides (chacune étant une liste de colonnes)
            - Liste des problèmes détectés (hors lignes vides)
        """
        logger.debug(f"Reading CSV file: {filepath}")
        problems = []
        lines = []
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                file_content = [(i+1, line.strip()) for i, line in enumerate(f) if line.strip()]
            
            if not file_content:
                problems.append("Le fichier est vide")
                return [], problems

            line_numbers = [num for num, _ in file_content]
            content = [line for _, line in file_content]

            header_line_num = line_numbers[0]
            header = content[0]
            if ';' not in header:
                problems.append(f"Ligne {header_line_num} : En-tête invalide, format attendu 'code;libellé' (contenu: '{header}')")

            for i in range(1, len(content)):
                line_num = line_numbers[i]
                line = content[i]

                if ';' not in line:
                    problems.append(f"Ligne {line_num} : Format invalide, attendu 'code;libellé' (contenu: '{line}')")
                    continue

                columns = [col.strip() for col in line.split(';', 1)]
                if len(columns) < 2:
                    problems.append(f"Ligne {line_num} : Format invalide, colonnes manquantes (contenu: '{line}')")
                    continue
                    
                lines.append(columns)
            
            return lines, problems
            
        except UnicodeDecodeError:
            problems.append("Erreur d'encodage : le fichier n'est pas en UTF-8")
            return [], problems
        except Exception as e:
            problems.append(f"Erreur lors de la lecture du fichier : {str(e)}")
            return [], problems

    def check_csv_integrity(self, filename: str) -> List[str]:
        """
        Vérifie l'intégrité d'un fichier CSV.

        Args:
            filename (str): Nom du fichier à vérifier
            
        Returns:
            List[str]: Liste des problèmes détectés (vide si aucun problème)
        """
        logger.debug(f"Checking integrity of {filename}")
        problems = []
        filepath = self.directory / filename
        
        if not filepath.exists():
            return [f"Fichier introuvable : {filename}"]

        lines, read_problems = self._read_csv_file(filepath)
        problems.extend(read_problems)
        
        if not lines:
            return problems

        header = lines[0]
        if len(header) < 2:
            problems.append("En-tête invalide : format attendu 'code;libellé'")

        if filename == "DEPCO.csv": # DEPCO.csv ne peut pas avoir une clef négative ou égale à 0. elle a donc un def spécifique
            problems.extend(self._validate_depco_content(iter(lines[1:])))

        if len(lines) <= 1:
            problems.append("Aucune donnée valide trouvée dans le fichier")
        
        return problems

    def _format_problems(self, filename: str, problems: List[str]) -> List[str]:
        """Formate les problèmes pour un meilleur affichage."""
        formatted = []
        for problem in problems:
            if problem.startswith("Ligne"):
                formatted.append(f"{filename}: {problem}")
            else:
                formatted.append(f"{filename}: {problem}")
        return formatted

    def run_checks(self) -> Dict[str, Any]:
        """
        Exécute toutes les vérifications sur les fichiers CSV.
        
        Returns:
            Dict: Dictionnaire contenant le rapport de vérification avec les clés :
                - success (bool): True si aucun problème n'a été détecté
                - problems (bool): True si des problèmes ont été détectés
                - files (Dict[str, Dict]): Détails par fichier
                - summary (Dict): Résumé des vérifications
        """
        self._reset_state()
        files_report = {}

        self.check_files_exist()
        for filename in sorted(REQUIRED_FILES):
            file_report = {
                "exists": filename not in self.missing_files,
                "problems": [],
                "valid": False
            }
            
            if file_report["exists"]:
                problems = self.check_csv_integrity(filename)
                file_report["problems"] = problems
                file_report["valid"] = len(problems) == 0
                
                if file_report["valid"]:
                    self._valid_files.add(filename)
                
                self.problems.extend(self._format_problems(filename, problems))
            
            files_report[filename] = file_report

        report = {
            "success": len(self.problems) == 0,
            "problems": len(self.problems) > 0,
            "files": files_report,
            "summary": {
                "total_files": len(REQUIRED_FILES),
                "missing": len(self.missing_files),
                "with_errors": len([f for f in files_report.values() 
                                  if f["exists"] and not f["valid"]]),
                "valid": len(self._valid_files)
            }
        }
        
        return report

def check_csv_files(directory: str) -> Dict[str, Any]:
    """
    Vérifie les fichiers CSV dans le répertoire spécifié.
    
    Args:
        directory (str): Chemin vers le dossier contenant les fichiers CSV
        
    Returns:
        Dict: Résultat de la vérification avec les clés :
            - success (bool)
            - problems (bool)
            - list_problems (List[str])
            - missing_files (List[str])
            - checked_files (List[str])
            - valid_files (List[str])
    """
    logger.info(f"Starting CSV file validation in directory: {directory}")
    try:
        checker = CSVChecker(directory)
        result = checker.run_checks()
        if result.get('success'):
            logger.info("CSV validation completed successfully")
        else:
            logger.warning(f"CSV validation completed with issues: {result.get('list_problems', [])}")
        return result
    except Exception as e:
        logger.error(f"Error during CSV validation: {str(e)}", exc_info=True)
        return {
            'success': False,
            'problems': True,
            'list_problems': [f"Error during validation: {str(e)}"],
            'missing_files': [],
            'checked_files': [],
            'valid_files': []
        }