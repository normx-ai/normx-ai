#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from pathlib import Path

def is_latin1_encodable(text):
    """Vérifie si le texte peut être encodé en Latin-1 (ISO-8859-1)."""
    try:
        text.encode('iso-8859-1')
        return True
    except UnicodeEncodeError:
        return False

def detect_simple_encoding(file_path):
    """Détecte si l'encodage est probablement ISO-8859-1 ou UTF-8."""
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            
        # Essayer UTF-8
        try:
            content = raw_data.decode('utf-8')
            return 'utf-8', raw_data
        except UnicodeDecodeError:
            pass
        
        # Essayer ISO-8859-1
        try:
            content = raw_data.decode('iso-8859-1')
            # Vérifier si c'est vraiment ISO-8859-1
            if is_latin1_encodable(content):
                return 'iso-8859-1', raw_data
        except UnicodeDecodeError:
            pass
        
        # Défaut ISO-8859-1 si aucun n'a marché
        return 'iso-8859-1', raw_data
    except Exception as e:
        print(f"Erreur lors de la détection de l'encodage pour {file_path}: {e}")
        return None, None

def convert_to_utf8(file_path, raw_data=None, source_encoding=None):
    """Convertit un fichier en UTF-8."""
    if raw_data is None or source_encoding is None:
        source_encoding, raw_data = detect_simple_encoding(file_path)
    
    if source_encoding is None:
        print(f"Impossible de détecter l'encodage pour {file_path}")
        return False
    
    if source_encoding.lower() == 'utf-8':
        print(f"Le fichier {file_path} est déjà en UTF-8")
        return True
    
    try:
        content = raw_data.decode(source_encoding)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fichier converti: {file_path} (de {source_encoding} à UTF-8)")
        return True
    except Exception as e:
        print(f"Erreur lors de la conversion de {file_path}: {e}")
        return False

def process_directory(directory):
    """Traite tous les fichiers HTML dans un répertoire et ses sous-répertoires."""
    templates_dir = Path(directory)
    count = 0
    
    for file_path in templates_dir.glob('**/*.html'):
        try:
            encoding, raw_data = detect_simple_encoding(file_path)
            if encoding and encoding.lower() != 'utf-8':
                if convert_to_utf8(file_path, raw_data, encoding):
                    count += 1
        except Exception as e:
            print(f"Erreur pour {file_path}: {e}")
    
    print(f"\n{count} fichiers convertis en UTF-8")

if __name__ == "__main__":
    templates_dir = "/home/chris/normx-ai/apps/users/templates"
    print(f"Conversion des fichiers templates en UTF-8 dans {templates_dir}...")
    
    if not os.path.exists(templates_dir):
        print(f"Le répertoire {templates_dir} n'existe pas.")
        sys.exit(1)
    
    process_directory(templates_dir)