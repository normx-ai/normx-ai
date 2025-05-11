#!/bin/bash

# Script pour convertir les fichiers de template HTML d'ISO-8859 à UTF-8
# Usage: ./fix_templates_encoding.sh

find ./apps/users/templates -name "*.html" -type f | while read -r file; do
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
        echo "Conversion completed for $file"
    else
        echo "$file is already in $encoding encoding, skipping"
    fi
done

echo "All files processed."