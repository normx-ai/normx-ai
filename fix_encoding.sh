#!/bin/bash

# Script pour convertir les fichiers Python d'ISO-8859 à UTF-8
# Usage: ./fix_encoding.sh <directory>

directory=${1:-"/home/chris/normx-ai/apps/users"}

find "$directory" -name "*.py" | while read -r file; do
    # Vérifier l'encodage actuel
    encoding=$(file -bi "$file" | sed -n 's/.*charset=\([^;]*\).*/\1/p')
    
    if [ "$encoding" != "utf-8" ] && [ "$encoding" != "us-ascii" ]; then
        echo "Converting $file from $encoding to UTF-8"
        # Créer un fichier temporaire
        tmp_file=$(mktemp)
        # Convertir le fichier
        iconv -f "$encoding" -t UTF-8 "$file" > "$tmp_file"
        # Remplacer le fichier original
        mv "$tmp_file" "$file"
        # Ajouter l'encodage UTF-8 en commentaire en haut du fichier
        sed -i '1s/^/# -*- coding: utf-8 -*-\n/' "$file"
        echo "Conversion completed for $file"
    else
        echo "$file is already in $encoding encoding, skipping"
    fi
done

echo "All files processed."