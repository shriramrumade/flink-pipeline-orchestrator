from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
import psycopg2
import sys

def fetch_pipeline_config(pipeline_id):
    conn = psycopg2.connect(
        host="postgres",
        database="metadata",
        user="flink",
        password="flink"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pipelines WHERE pipeline_id = %s", (pipeline_id,))
    row = cursor.fetchone()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return dict(zip(columns, row))

def register_source(table_env, config):
    table_env.execute_sql(f'''
        CREATE TABLE source_table (
            data STRING
        ) WITH (
            'connector' = 'filesystem',
            'path' = '{config["source_path"]}',
            'format' = '{config["source_format"]}'
        )
    ''')

def register_sink(table_env, config):
    table_env.execute_sql('''
        CREATE TABLE sink_table (
            data STRING
        ) WITH (
            'connector' = 'print'
        )
    ''')

def run_pipeline(pipeline_id):
    config = fetch_pipeline_config(pipeline_id)
    env_settings = EnvironmentSettings.in_streaming_mode()
    env = StreamExecutionEnvironment.get_execution_environment()
    table_env = StreamTableEnvironment.create(env, env_settings)

    register_source(table_env, config)
    table_env.execute_sql("""CREATE TEMPORARY VIEW transformed AS SELECT UPPER(data) as data FROM source_table""")
    register_sink(table_env, config)
    table_env.execute_sql("""INSERT INTO sink_table SELECT * FROM transformed""")

    env.execute(f"pipeline_{pipeline_id}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python main.py <pipeline_id>")
        sys.exit(1)
    run_pipeline(sys.argv[1])
