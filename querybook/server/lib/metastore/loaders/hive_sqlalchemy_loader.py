from typing import List, Tuple, Optional

from sqlalchemy import text

from lib.metastore.base_metastore_loader import DataTable, DataColumn
from lib.metastore.loaders.sqlalchemy_metastore_loader import SqlAlchemyMetastoreLoader
from lib.logger import get_logger

LOG = get_logger(__name__)

class HiveSqlAlchemyLoader(SqlAlchemyMetastoreLoader):
    def get_all_schema_names(self) -> List[str]:
        with self._engine.connect() as connection:
            schemas = connection.execute(text('select "NAME" from "DBS"'))
            return [row['NAME'] for row in schemas if row['NAME'] != 'abt_metric']

    def get_all_table_names_in_schema(self, schema_name: str) -> List[str]:
        with self._engine.connect() as connection:
            result = connection.execute(text(f"""
                select 
                    "TBL_NAME" as table_name 
                from 
                    "TBLS" as tbls 
                inner join "DBS" as dbs on dbs."DB_ID" = tbls."DB_ID"
                where
                    dbs."NAME" = '{schema_name}'
            """))
            return [row['table_name'] for row in result]

    def get_table_and_columns(
        self, schema_name, table_name
    ) -> Tuple[Optional[DataTable], List[DataColumn]]:
        table = DataTable(
            name=table_name,
            type=None,
            owner=None,
            table_created_at=None,
            table_updated_by=None,
            table_updated_at=None,
            data_size_bytes=None,
            location=None,
            partitions=None,
            raw_description="",
        )

        with self._engine.connect() as connection:
            columns_result = connection.execute(text(f"""
                select 
                    "COLUMN_NAME" as col_name,
                    "TYPE_NAME" as type_name 
                from 
                    "COLUMNS_V2" as cols
                inner join "SDS" as sds on sds."CD_ID" = cols."CD_ID"
                inner join "TBLS" as tbls on tbls."SD_ID" = sds."SD_ID"
                inner join "DBS" as dbs on dbs."DB_ID" = tbls."DB_ID"
                where
                    dbs."NAME" = '{schema_name}'
                    AND tbls."TBL_NAME" = '{table_name}'
            """))

            partitions_result = connection.execute(text(f"""
                select 
                    "PKEY_NAME" as col_name,
                    "PKEY_TYPE" as type_name 
                from 
                    "PARTITION_KEYS" as cols
                inner join "TBLS" as tbls on tbls."TBL_ID" = cols."TBL_ID"
                inner join "DBS" as dbs on dbs."DB_ID" = tbls."DB_ID"
                where
                    dbs."NAME" = '{schema_name}'
                    AND tbls."TBL_NAME" = '{table_name}'
            """))

        if not columns_result and not partitions_result:
            return None, []

        def row_converter(row):
            return DataColumn(
                name=row['col_name'],
                type=str(row['type_name']),
                comment='',
            )

        columns = list(map(row_converter, list(columns_result) + list(partitions_result)))
        LOG.info(f'Got data for schema {schema_name} table {table} columns num: {len(columns)}')

        return table, columns
