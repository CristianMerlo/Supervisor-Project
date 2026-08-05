#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo: gestor_hashes.py
Ubicación: /home/cristian/PROYECTOS/Supervisor-Project/

Descripción:
Genera firmas criptográficas SHA-256 de archivos PDF e ingesta para evitar la
duplicación cruzada entre Gmail, Telegram o cargas manuales por pendrive.
Mantiene la base SQLite hashes_procesados.db.
"""

import os
import hashlib
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("gestor_hashes")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

BASE_DIR = Path(__file__).parent
DB_PATH_DOC = Path("/home/cristian/Documentos/Supervisor/hashes_procesados.db")
DB_PATH_PROJ = BASE_DIR / "brain" / "hashes_procesados.db"

def obtener_conexion_db():
    """Conecta a la base de datos de hashes en Documentos/Supervisor (o fallback local)."""
    target_db = DB_PATH_DOC if DB_PATH_DOC.parent.exists() else DB_PATH_PROJ
    target_db.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(target_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hashes_reportes (
            hash TEXT PRIMARY KEY,
            fecha_registro TEXT,
            origen TEXT,
            nombre_archivo TEXT,
            sigla TEXT
        );
    """)
    conn.commit()
    return conn

def calcular_sha256(file_path):
    """Calcula el hash SHA-256 de un archivo binario."""
    file_path = Path(file_path)
    if not file_path.exists() or not file_path.is_file():
        return None
        
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(65536), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().lower()
    except Exception as e:
        logger.error(f"Error calculando SHA-256 para {file_path}: {e}")
        return None

def es_reporte_duplicado(file_path):
    """
    Verifica si el archivo PDF ya fue procesado previamente
    comparando su firma SHA-256 en la base de datos.
    Returns: (is_duplicate: bool, hash_val: str, info_registro: dict|None)
    """
    hash_val = calcular_sha256(file_path)
    if not hash_val:
        return False, None, None
        
    try:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute("SELECT hash, fecha_registro, origen, nombre_archivo, sigla FROM hashes_reportes WHERE hash = ?", (hash_val,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            info = dict(row)
            return True, hash_val, info
        return False, hash_val, None
    except Exception as e:
        logger.error(f"Error consultando hash en DB: {e}")
        return False, hash_val, None

def registrar_reporte(file_path, origen="Desconocido", sigla=""):
    """Registra la firma SHA-256 de un reporte recién procesado."""
    hash_val = calcular_sha256(file_path)
    if not hash_val:
        return False
        
    nombre_archivo = Path(file_path).name
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR IGNORE INTO hashes_reportes (hash, fecha_registro, origen, nombre_archivo, sigla)
            VALUES (?, ?, ?, ?, ?)
        """, (hash_val, fecha_actual, origen, nombre_archivo, sigla))
        conn.commit()
        conn.close()
        logger.info(f"[HASH-REGISTRADO] SHA-256: {hash_val[:10]}... | Archivo: {nombre_archivo} | Origen: {origen}")
        return True
    except Exception as e:
        logger.error(f"Error registrando hash SHA-256: {e}")
        return False

def obtener_total_hashes_registrados():
    """Retorna la cantidad total de reportes únicos resguardados por firma SHA-256."""
    try:
        conn = obtener_conexion_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM hashes_reportes")
        total = cursor.fetchone()[0]
        conn.close()
        return total
    except Exception:
        return 0

def backfill_pdfs_existentes():
    """Indexa todos los PDFs existentes en PDFs_Originales/ y procesados/ para poblar la DB."""
    directorios = [
        BASE_DIR / "brain" / "locales" / "PDFs_Originales",
        BASE_DIR / "procesados"
    ]
    total_indexados = 0
    for d in directorios:
        if d.exists():
            for pdf_file in d.glob("*.pdf"):
                if registrar_reporte(pdf_file, origen="Backfill Historico"):
                    total_indexados += 1
    return total_indexados

if __name__ == "__main__":
    logger.info("Iniciando indexación inicial (Backfill) de firmas SHA-256 de PDFs existentes...")
    count = backfill_pdfs_existentes()
    total = obtener_total_hashes_registrados()
    logger.info(f"[✓] Backfill finalizado. Indexados en esta carrera: {count} | Total único en DB: {total}")
