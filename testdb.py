import psycopg2
from psycopg2 import OperationalError
from urllib.parse import urlparse
postgres_url = "postgres://default:KHS7RdOxCEp1@ep-lively-poetry-a4k7k20v.us-east-1.aws.neon.tech:5432/verceldb?sslmode=require"
parsed_url = urlparse(postgres_url)

# Establishing connection=
conn = psycopg2.connect(
    dbname=parsed_url.path[1:],
    user=parsed_url.username,
    password=parsed_url.password,
    host=parsed_url.hostname,
    port=parsed_url.port
)


db = conn.cursor()

query="select * from users"
db.execute()
result=db.fetchall()

for i in result:
 print(i)


db.close()
conn.close()