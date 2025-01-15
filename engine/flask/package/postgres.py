import os 
from package.connections import Connections

class Postgres:
    def __init__(self):
        self.connection = Connections(postgres_database=os.getenv('POSTGRES_DB_NAME'),
                    postgres_host=os.getenv('POSTGRES_DB_HOST'),
                    postgres_password=os.getenv('POSTGRES_DB_PASSWORD'),
                    postgres_username=os.getenv('POSTGRES_DB_USERNAME'),
                    postgres_port=os.getenv('POSTGRES_DB_PORT'))
        self.pg_conn = self.connection.postgres_connection()
        
    def get_data_executor(self,query):
        pg_curr = self.pg_conn.cursor()
        pg_curr.execute(query)
        data = pg_curr.fetchall()
        return data 
    
    def update_logs(self,query):
        pg_curr = self.pg_conn.cursor()
        pg_curr.execute(query)
        self.pg_conn.commit()
        self.pg_conn.close()