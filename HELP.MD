# Documentation du plugin DourBase

## Table des matières
1. [Présentation](#présentation)
2. [Installation](#installation)
3. [Utilisation](#utilisation)
   - [Onglet "Imports"](#onglet-imports)
   - [Onglet "Identifiants GEODIS"](#onglet-identifiants-geodis)
   - [Onglet "Déploiement"](#onglet-déploiement)
   - [Onglet "Paramètres"](#onglet-paramètres)
. [Dépannage](#dépannage)

## Présentation

DourBase est une extension QGIS conçue pour simplifier l'intégration des plans de récolement conformes au cahier des charges GéoPaysdeBrest. Elle inclut également la gestion des identifiants grâce au plugin rsxident de Géodis. De plus, elle permet de mettre à jour les données entre la base de travail et la base de consultation.

## Installation

### Installation depuis un ZIP
1. Téléchargez le plugin au format ZIP depuis le dépôt officiel
2. Dans QGIS, allez dans `Extensions` > `Installer/Gérer les extensions...`
3. Cliquez sur l'onglet `Installation depuis un ZIP`
4. Sélectionnez le fichier ZIP téléchargé
. Une bannière de bienvenue s'affichera au premier démarrage

### Installation depuis un dépôt
1. Dans QGIS, allez dans `Extensions` > `Installer/Gérer les extensions...`
2. Cliquez sur l'onglet `Tout`
3. Recherchez `DourBase` si non visible
4. Cliquez sur `Installer le plugin` en bas à droite
5. Si le bouton ne s'affiche pas dans la fenêtre,Redémarrez QGIS
6. Une bannière de bienvenue s'affichera au premier démarrage

## Utilisation

### Onglet "Imports"

#### 1. Sélection du dossier source
- Cliquez sur **Importer le dossier** pour sélectionner le dossier contenant les fichiers Shapefile à importer
- Le dossier doit contenir les fichiers .shp ainsi que les fichiers associés (.shx, .dbf, etc.)

#### 2. Paramètres d'importation
- **Numéro source** : Entrez un numéro à 3 chiffres (ex: 001) qui sera utilisé comme partie de l'identifiant source dans BASEDOC
- **Base de données** : Sélectionnez la base de données PostGIS de destination dans la liste déroulante
- **Exploitant** : Sélectionnez l'exploitant du réseau (ex: CLCL, CAPLD, etc.)
- **Commune (DEPCO)** : Sélectionnez la commune concernée par l'import (code INSEE)
- **Type de réseau** : Cochez le(s) type(s) de réseau concerné(s) (AEP, EU ou EPL)
- **Localisation** : Saisissez la localisation précise (ex: nom de rue)
- **Type de plan** : Indiquez le type de plan (ex: Plan de récolement)
- **Bureau d'études** : Précisez le bureau d'études responsable
- **Entreprise** : Sélectionnez l'entreprise en charge des travaux
- **Date du plan** : Définissez la date de réalisation du plan
- **Échelle** : Indiquez l'échelle du plan (ex: 200 pour 1/200)
- **Plan côté** : Cochez si le plan est côté
- **Type de support** : Sélectionnez le type de support du plan
- **Qualité du support** : Sélectionnez la qualité du support
- **Utilisation du plan** : Cochez si le plan est utilisé pour la numérisation
- **Maître d'ouvrage (MOA)** : Sélectionnez le maître d'ouvrage

#### 3. Validation
- Le nom de fichier généré s'affiche automatiquement en fonction des paramètres. Si celui-ci ne vous convient pas, vous pouvez le modifier manuellement.
- Cliquez sur **Insérer dans la base** pour lancer l'importation.

### Onglet "Identifiants GEODIS"

Cet onglet permet d'accéder rapidement aux identifiants des différents réseaux via le plugin RsxIdent (doit être installé séparément. À noter, DourBase vous permet de l'installer si ce n'est pas déjà fait).

- **Boutons d'accès rapide** :
  - Icône bleue : Accès aux identifiants AEP
  - Icône verte : Accès aux identifiants EPL
  - Icône rouge : Accès aux identifiants EU

Si le plugin RsxIdent n'est pas installé, un message d'erreur s'affiche avec un bouton pour l'installer.

### Onglet "Déploiement"

Permet de gérer le déploiement des bases de données.

#### 1. Sélection des bases
- **Base de données de travail** : Sélectionnez la base source
- **Base de données de consultation** : Sélectionnez la base de destination
- Un avertissement s'affiche si les deux bases sont identiques

#### 2. Authentification
- **Nom d'utilisateur** : Saisissez votre identifiant de base de données
- **Mot de passe** : Saisissez votre mot de passe

#### 3. Sauvegardes
- **Sauvegarde PostGIS** : Dossier pour la sauvegarde de la base PostGIS
- **Sauvegarde consultation** : Dossier pour la sauvegarde de la base de consultation

#### 4. Déploiement
- Cliquez sur **Déployer** pour lancer le processus de déploiement

**Note :** Si les deux bases sont identiques, qu'un champ est vide, ou que les dossiers de sauvegarde ne sont pas renseignés, le bouton `Déployer` sera grisé.
### Onglet "Paramètres"

#### 1. Configuration des dossiers
- **Dossier des CSV** : Affiche le chemin actuel du dossier de configuration si vous n'utilisez pas le dossier par défaut
- **Sélectionner** : Permet de choisir un nouveau dossier de configuration
- **Réinitialiser** : Remet le dossier de configuration par défaut

#### 2. Support
- Lien vers la page des issues GitHub pour signaler des problèmes, poser des questions ou demander de l'aide.

### Journalisation
- Toutes les opérations sont enregistrées dans un journal
- Possibilité d'exporter les journaux pour analyse


## Dépannage

### Problèmes courants

#### 1. Erreur de connexion à la base de données
- Vérifiez que le serveur PostgreSQL est accessible
- Vérifiez les identifiants de connexion
- Assurez-vous que l'utilisateur a les droits nécessaires
- Verifiez que vous n'avez pas de caractères spéciaux dans le mot de passe (le caractère `"` est supporté.)

#### 3. Plugin RsxIdent non détecté
- Assurez-vous que le plugin RsxIdent est installé et activé
- Vérifiez qu'il est à jour

### Support technique
Pour toute question, problème, suggestion, ou demande d'aide, vous pouvez ouvrir une issue sur le dépôt GitHub : [https://github.com/SIG-CLCL/DourBase/issues](https://github.com/SIG-CLCL/DourBase/issues)

---

*Dernière mise à jour : 27/06/2025*
*Version du plugin : 1.0*
