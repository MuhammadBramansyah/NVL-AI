import paramiko
import psycopg2
from cassandra.cluster import Cluster
import boto3
from botocore.config import Config
from cassandra.auth import PlainTextAuthProvider

class Connections:
    def __init__(self, postgres_host=None, postgres_username=None, postgres_password=None, postgres_database=None, postgres_port=None,
                 cassandra_host=None, cassandra_username=None, cassandra_password=None, cassandra_keyspace=None, cassandra_port=None,
                 sftp_host = None, sftp_username = None,sftp_password = None, sftp_port = None,
                 s3_acces_key = None,s3_secret_key = None,s3_region = None,s3_endpoint = None):

        self.postgres_host = postgres_host
        self.postgres_username = postgres_username
        self.postgres_password = postgres_password
        self.postgres_database = postgres_database
        self.postgres_port = postgres_port
        self.cassandra_host = cassandra_host
        self.cassandra_username = cassandra_username
        self.cassandra_password = cassandra_password
        self.cassandra_keyspace = cassandra_keyspace
        self.cassandra_port = cassandra_port
        self.sftp_host = sftp_host
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_port = sftp_port 
        self.s3_access_key = s3_acces_key
        self.s3_secret_key = s3_secret_key
        self.s3_region = s3_region
        self.s3_endpoint = s3_endpoint
    
    def sftp_connection(self):
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname= self.sftp_host, username = self.sftp_username, password = self.sftp_password, port = self.sftp_port)
        return ssh_client.open_sftp()
        
    def s3_connection(self):
        config = Config(
            region_name = self.s3_region,
            retries = {
                'max_attempts':10,
                'mode': 'standard'
            }
        )

        return boto3.client(
            service_name = 's3',
            endpoint_url = self.s3_endpoint,
            aws_access_key_id = self.s3_access_key,
            aws_secret_access_key = self.s3_secret_key,
            verify = False,
            config = config
        )

    def postgres_connection(self):  
        while True:
            try:
                conn = psycopg2.connect(
                    host = self.postgres_host,
                    user = self.postgres_username,
                    password = self.postgres_password,
                    database = self.postgres_database,
                    port = self.postgres_port
                    # host = "localhost",
                    # user = "postgres",
                    # password = "PCo2Msj7Ho",
                    # database = "recon_db2",
                    # port = 5432
                )
                break
            except:
                raise Exception("Cant Connect To Postgres DB") 
        return conn

    def cassandra_connection(self):
        user_credential = PlainTextAuthProvider(username=self.cassandra_username, password=self.cassandra_password)

        cluster = Cluster(
            [self.cassandra_host],
            port=self.cassandra_port,
            auth_provider=user_credential
        )

        while True:
            try:
                conn = cluster.connect(
                    self.cassandra_keyspace
                )
                break
            except:
                raise Exception("Can't connect to Cassandra DB")
        return conn

  
    
