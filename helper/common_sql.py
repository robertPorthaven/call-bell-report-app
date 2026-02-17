import pandas as pd
import logging
import pyodbc
import struct
from sqlalchemy import create_engine, text
from azure.identity import DefaultAzureCredential
from functools import partial
import uuid
import json
import datetime

# Configure logger for this module
logger = logging.getLogger(__name__)
logger.propagate = True

class SqlThings:
    """Database operations handler with consistent connection management."""

    def __init__(self, sql_server_name, database_name, app_name):
        """
        Initialize SqlThing with database connection.
        """
        self.database_name = database_name
        self.sql_server_name = sql_server_name
        self.engine = self._create_engine(sql_server_name, database_name, app_name)
        logger.info(f"SqlThings initialized for database: {database_name}")

    def connect_with_token(self, base_connect: str):
        """
        Creates a pyodbc connection using an Azure AD access token.
        """
        try:
            credential = DefaultAzureCredential()
            token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("utf-16le")
            # Pack token with 4-byte little-endian length prefix
            token_struct = struct.pack(
                f"<I{len(token_bytes)}s",
                len(token_bytes),
                token_bytes
            )
            return pyodbc.connect(base_connect, attrs_before={1256: token_struct})
        except Exception as e:
            logger.error(f"Failed to acquire Azure AD token for {self.database_name}: {e}", exc_info=True)
            raise

    def _create_engine(self, sql_server_name: str, database_name: str, app_name: str):
        """
        Creates a SQLAlchemy engine using Azure AD token-based authentication.
        """
        try:
            db_driver = "{ODBC Driver 18 for SQL Server}"
            base_connect = (
                f"Driver={db_driver};"
                f"Server=tcp:{sql_server_name},1433;"
                f"Database={database_name};"
                "Encrypt=yes;"
                "TrustServerCertificate=no;"
                "Connection Timeout=30;"
                f"APP={app_name};"
            )
            engine = create_engine(
                "mssql+pyodbc://",
                creator=partial(self.connect_with_token, base_connect),
                fast_executemany=True,
                pool_pre_ping=True
            )
            logger.info(f"Connected to database '{database_name}' on server '{sql_server_name}'.")
            return engine
        except Exception as e:
            logger.critical(f"Failed to connect to database '{database_name}': {e}", exc_info=True)
            raise RuntimeError(f"Database connection failed for '{database_name}'") from e

    def _execute_query(self, query, params=None, data_label=None):
        """
        Executes query and stamps the data_label into the response.
        Automatically wraps raw strings in SQLAlchemy text() objects.
        """
        if isinstance(query, str):
            query = text(query)
        with self.engine.begin() as connection:
            try:
                result = connection.execute(query, params or {})
                if result.returns_rows:
                    raw_response = result.scalar_one_or_none()
                    if raw_response:
                        try:
                            parsed_json = json.loads(raw_response)
                            if isinstance(parsed_json, dict):
                                parsed_json["DataLabel"] = data_label
                                logger.info(f"JSON_METRICS: {json.dumps(parsed_json)}")
                            return parsed_json
                        except (ValueError, TypeError):
                            msg = f"[{data_label}] {raw_response}" if data_label else raw_response
                            logger.info(f"SQL_MESSAGE: {msg}")
                            return raw_response
                return None
            except Exception as e:
                logger.error(f"Error executing SQL on {self.database_name}: {e}", exc_info=True)
                raise

    def view_to_map(self, view_name, view_schema):
        """
        Returns a dictionary mapping the first column to a dict of all other columns.
        """
        query = text(f"SELECT * FROM [{view_schema}].[{view_name}]")
        with self.engine.connect() as connection:
            df = pd.read_sql(query, connection)
        if df.empty:
            logger.warning(f"View {view_schema}.{view_name} returned no data")
            return {}
        first_col = df.columns[0]
        return df.set_index(first_col).to_dict('index')

    # ------------------------------
    # One-shot temp stage uploads
    # ------------------------------
    def _upload_to_temp(self, data_df):
        """
        Uploads a DataFrame to a staging table in schema 'temp'.
        """
        if data_df.empty:
            raise ValueError("DataFrame is empty. Nothing to upload.")
        schema = "temp"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        table = f"staged_{timestamp}_{uuid.uuid4().hex[:4]}"
        with self.engine.begin() as connection:
            try:
                data_df.to_sql(
                    name=table,
                    con=connection,
                    schema=schema,
                    if_exists="fail",
                    index=False,
                    chunksize=None,
                )
                logger.debug(f"Uploaded {len(data_df)} rows to {schema}.{table}")
                return table
            except Exception as e:
                logger.error(f"Error uploading to {schema}.{table} on {self.database_name}: {e}", exc_info=True)
                raise

    def _execute_stored_procedure(self, proc_name, schema, params, data_label=None):
        """
        Executes SP and captures the final SELECT result.
        """
        sql_params = ", ".join([f"@{k} = :{k}" for k in params.keys()])
        query = text(f"EXEC {schema}.{proc_name} {sql_params}")
        return self._execute_query(query, params, data_label)


    def upsert_data(self, data_df, target_table, target_schema, data_label=None):
        source_table = self._upload_to_temp(data_df)
        params = {
            "target_table": target_table,
            "target_schema": target_schema,
            "upload_table": source_table,
            "upload_schema": 'temp',
        }
        self._execute_stored_procedure("sp_upsert_data", "apps", params, data_label)
        self._execute_query(f'DROP TABLE [temp].[{source_table}]')

    def merge_data_full(self, data_df, target_table, target_schema, data_label=None):
        source_table = self._upload_to_temp(data_df)
        params = {
            "target_table": target_table,
            "target_schema": target_schema,
            "upload_table": source_table,
            "upload_schema": 'temp',
        }
        self._execute_stored_procedure("sp_merge_data_full", "apps", params, data_label)
        self._execute_query(f'DROP TABLE [temp].[{source_table}]')

    def bulk_update_scoped(self, data_df, target_table, target_schema, scope_column, data_label=None):
        source_table = self._upload_to_temp(data_df)
        params = {
            "target_table": target_table,
            "target_schema": target_schema,
            "upload_table": source_table,
            "upload_schema": 'temp',
            "scope_column": scope_column,
        }
        self._execute_stored_procedure("sp_bulk_update_scoped", "apps", params, data_label)
        self._execute_query(f'DROP TABLE [temp].[{source_table}]')

    def merge_data_scoped(self, data_df, table_name, schema, scope_column, data_label=None):
        source_table = self._upload_to_temp(data_df)
        params = {
            "target_table": table_name,
            "target_schema": schema,
            "upload_table": source_table,
            "upload_schema": "temp",
            "scope_column": scope_column
        }
        result = self._execute_stored_procedure("sp_merge_data_scoped", "apps", params, data_label)
        self._execute_query(f'DROP TABLE [temp].[{source_table}]')
        return result

    # ------------------------------
    # Permanent Stage upload
    # ------------------------------
    def truncate_table(self, *, schema: str, table: str) -> None:
        """
        TRUNCATE the permanent staging table.
        """
        with self.engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE [{schema}].[{table}]"))
        logger.info(f"Truncated {schema}.{table}")

    def append_to_apps_stage(self, data_df: pd.DataFrame, *, schema: str, table: str) -> None:
        """
        Append into [schema].[table].
        """
        if data_df.empty:
            return
        with self.engine.begin() as connection:
            data_df.to_sql(
                name=table,
                con=connection,
                schema=schema,
                if_exists="append",
                index=False,
                chunksize=None,
            )
        logger.debug(f"Appended {len(data_df)} rows to {schema}.{table}")

    def merge_data_full_from_apps_stage(
        self,
        *,
        stage_schema: str,
        stage_table: str,
        target_schema: str,
        target_table: str,
    ) -> None:
        """
        Executes apps.sp_merge_data_full once, using a permanent staging table.
        """
        params = {
            "target_table": target_table,
            "target_schema": target_schema,
            "upload_table": stage_table,
            "upload_schema": stage_schema,
        }
        self._execute_stored_procedure("sp_merge_data_full", "apps", params)
        logger.info(f"Merged from {stage_schema}.{stage_table} into {target_schema}.{target_table}")

        

    def read_tvf(self, schema: str, fn_name: str, *args, user_context: dict[str, str] | None = None  ) -> pd.DataFrame:

        placeholders = ", ".join([f":p{i}" for i in range(len(args))])
        params = {f"p{i}": v for i, v in enumerate(args)}

        sql = text(f"SELECT * FROM {schema}.{fn_name}({placeholders})")

        with self.engine.connect() as connection:
                if user_context:
                    self.set_user_context(connection, user_context)
                try:
                    df = pd.read_sql(sql, connection, params=params or {})
                    return df
                except Exception as e:
                    logger.error(f"Failed on {self.database_name}: {e}", exc_info=True)
                    raise


    
    def run_query_df(self, query: str, params: dict | None = None, user_context: dict[str, str] | None = None) -> pd.DataFrame:
        if isinstance(query, str):
            sql = text(query) 
            with self.engine.connect() as connection:
                if user_context:
                    self.set_user_context(connection, user_context)
                try:
                    df = pd.read_sql(sql, connection, params=params or {})
                    return df
                except Exception as e:
                    logger.error(f"Failed on {self.database_name}: {e}", exc_info=True)
                    raise

    def set_user_context(self, connection, user_context: dict[str, str]) -> None:
        """
        Applies key/value user context into the SQL session using sp_set_session_context.
        Uses positional parameters (?) because SQLAlchemy cannot parameterise system SPs.
        Filters out None values as SQL Server session context cannot store NULL.
        """
        # Filter out None, empty string, and ensure all values are strings
        filtered_context = {
            k: str(v) for k, v in user_context.items() 
            if v is not None and v != ""
        }
        
        logger.debug(f"Setting session context: {filtered_context}")
        
        for key, value in filtered_context.items():
            connection.exec_driver_sql(
                "EXEC sys.sp_set_session_context @key = ?, @value = ?",
                (key, value)
            )