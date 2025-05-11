# -*- coding: utf-8 -*-
import os
import logging
from logging.handlers import RotatingFileHandler

# Configuration du logger pour le débogage
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

LOG_FILE = os.path.join(LOG_DIR, 'debug.log')

# Configuration du logger
logger = logging.getLogger('normx_debug')
logger.setLevel(logging.DEBUG)

# Configuration du gestionnaire de fichiers
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=1024*1024*5, backupCount=5)
file_handler.setLevel(logging.DEBUG)

# Format des messages
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Ajout du gestionnaire au logger
logger.addHandler(file_handler)

# Fonction pratique pour le débogage
def log_debug(message):
    logger.debug(message)

def log_info(message):
    logger.info(message)

def log_error(message):
    logger.error(message)