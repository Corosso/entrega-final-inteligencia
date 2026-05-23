#!/usr/bin/env python3
"""
Conexión centralizada a SQL Server para todo el proyecto BI.
============================================================
Único punto de configuración de la base de datos. Todos los scripts
(ETL, SCD/cubos, análisis y dashboard) importan este módulo en lugar de
abrir conexiones por su cuenta.

Motor: SQL Server (conector pymssql, sin drivers ODBC del sistema).

Las bases viven en la misma instancia:
  - RetailOLTP : sistema transaccional (origen)
  - RetailDW   : Data Warehouse (destino)
"""

from sqlalchemy import create_engine, text

# Configuración de la instancia SQL Server.
# El password debe coincidir con MSSQL_SA_PASSWORD del contenedor Docker.
SQLSERVER = {
    "host": "localhost",
    "port": 1433,
    "user": "sa",
    "password": "TuPassword123!",
}

OLTP_DB = "RetailOLTP"   # base del sistema transaccional (origen)
DW_DB = "RetailDW"       # base del Data Warehouse (destino)


def get_engine(database):
    """Retorna un Engine de SQLAlchemy hacia la base indicada."""
    c = SQLSERVER
    url = (
        f"mssql+pymssql://{c['user']}:{c['password']}"
        f"@{c['host']}:{c['port']}/{database}?charset=utf8"
    )
    return create_engine(url)


def connect(database):
    """Retorna una Connection (tiene .close(), compatible con pd.read_sql / to_sql)."""
    return get_engine(database).connect()


def ensure_databases():
    """Crea RetailOLTP y RetailDW si no existen.

    CREATE DATABASE no puede ejecutarse dentro de una transacción, por eso se
    usa la base 'master' en modo AUTOCOMMIT.
    """
    engine = get_engine("master").execution_options(isolation_level="AUTOCOMMIT")
    with engine.connect() as cn:
        for db in (OLTP_DB, DW_DB):
            cn.execute(text(f"IF DB_ID('{db}') IS NULL CREATE DATABASE [{db}]"))
    engine.dispose()


def list_tables(conn):
    """Lista las tablas base de la conexión actual (reemplazo de sqlite_master)."""
    import pandas as pd
    return pd.read_sql(
        "SELECT TABLE_NAME AS name FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE'",
        conn,
    )
