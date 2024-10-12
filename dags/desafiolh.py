from airflow.utils.edgemodifier import Label
from datetime import datetime, timedelta
from textwrap import dedent
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow import DAG
from airflow.models import Variable
import pandas as pd
import sqlite3

default_args = {
    'owner': 'Kaue Oliveira',
    'depends_on_past': False,
    'email': ['kaue.oliveira@indicium.tech'],
    'email_on_failure': True,
    'email_on_retry': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}


def export_final_answer():
    import base64

    with open('count.txt') as f:
        count = f.readlines()[0]

    my_email = Variable.get("my_email")
    message = my_email+count
    message_bytes = message.encode('ascii')
    base64_bytes = base64.b64encode(message_bytes)
    base64_message = base64_bytes.decode('ascii')

    with open('/home/kaueoliveira/airflow/final_output.txt',"w") as f:
        f.write(base64_message)
    return None


def export_orders_to_csv():
    conn = sqlite3.connect('/home/kaueoliveira/airflow/data/Northwind_small.sqlite')
    
    query = 'SELECT * FROM "Order";'
    df = pd.read_sql_query(query, conn)
    
    conn.close()
    
    output_file = '/home/kaueoliveira/airflow/output_orders.csv'
    df.to_csv(output_file, index=False)

def calculate_quantity_rio():

    orders_df = pd.read_csv('/home/kaueoliveira/airflow/output_orders.csv')

    print("Colunas em orders_df:", orders_df.columns.tolist())

    conn = sqlite3.connect('/home/kaueoliveira/airflow/data/Northwind_small.sqlite')

    order_detail_query = 'SELECT * FROM "OrderDetail";'
    order_details_df = pd.read_sql_query(order_detail_query, conn)

    conn.close()

    print("Colunas em order_details_df:", order_details_df.columns.tolist())

    merged_df = pd.merge(orders_df, order_details_df, left_on='Id', right_on='OrderId')

    rio_sales = merged_df[merged_df['ShipCity'] == 'Rio de Janeiro']

    total_quantity = rio_sales['Quantity'].sum()

    with open('/home/kaueoliveira/airflow/count.txt', 'w') as f:
        f.write(str(total_quantity))

with DAG(
    'DesafioLH',
    default_args=default_args,
    description='Resposta ao Desafio de Airflow da Indicium',
    schedule_interval=timedelta(days=1),
    start_date=datetime(2021, 1, 1),
    catchup=False,
    tags=['desafio'],
) as dag:
    dag.doc_md = """
        Essa é a entrega do desafio de Airflow da Indicium.
    """
   
    export_final_output = PythonOperator(
        task_id='export_final_output',
        python_callable=export_final_answer,
        provide_context=True
    )

     # Task para exportar dados da tabela Order
    export_orders_task = PythonOperator(
        task_id='export_orders',
        python_callable=export_orders_to_csv,
    )

    # Task para calcular a quantidade para Rio de Janeiro
    calculate_quantity_task = PythonOperator(
        task_id='calculate_quantity_rio',
        python_callable=calculate_quantity_rio,
    )

    # Definindo a ordem das tasks
    export_orders_task >> calculate_quantity_task >> export_final_output

