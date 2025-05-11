#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

def clear_data():
    """Supprimer les sessions et cookies pour repartir sur une base propre"""
    os.system('rm -rf /tmp/django_*')
    print("Sessions et caches supprimés")

def print_logs():
    """Afficher les fichiers de log"""
    os.system('find /var/log/apache2/ -name "*error*" -type f | xargs tail -n 100')
    print("------------------------------------")
    os.system('find /var/log/nginx/ -name "*error*" -type f | xargs tail -n 100')

if __name__ == "__main__":
    clear_data()
    print_logs()