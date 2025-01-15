from package.connections import Connections

class Postgres:
    def __init__(self):
        self.connection = Connections(postgres_database='vidan_test',
                    postgres_host='localhost',
                    postgres_password='PCo2Msj7Ho',
                    postgres_username='postgres',
                    postgres_port=5432)
        self.pg_conn = self.connection.postgres_connection()
        
    def get_data_executor(self,query):
        pg_curr = self.pg_conn.cursor()
        pg_curr.execute(query)
        data = pg_curr.fetchall()
        return data 