import boto3
import streamlit as st
from decimal import Decimal
import time

# Initialize DynamoDB client
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-west-1', 
    aws_access_key_id='AKIAXQIQARFMAYHZZ2AW',  
    aws_secret_access_key='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' 
)


table = dynamodb.Table('PerformersScores')

# Define a mapping between DynamoDB keys and custom column names
column_mapping = {
    'performer_id': 'Performer ID',
    'judge1_score': 'Judge 1 score',
    'judge2_score': 'Judge 2 score',
    'judge3_score': 'Judge 3 score',
}

# Function to compute final score
def compute_final_score(judge1, judge2, judge3):
   
    return (0.5 * float(judge1)) + (0.25 * float(judge2)) + (0.25 * float(judge3))

def map_columns_with_final_score(data):
    mapped_data = []
    for item in data:
        # Map the columns
        new_item = {column_mapping.get(k, k): v for k, v in item.items()}
        
        
        final_score = compute_final_score(
            item.get('judge1_score', Decimal(0)),
            item.get('judge2_score', Decimal(0)),
            item.get('judge3_score', Decimal(0))
        )
        new_item['Final Score'] = final_score  # Add final score column

        mapped_data.append(new_item)
    return mapped_data


def fetch_all_data():
    try:
        # Retrieve all items from the table
        response = table.scan()
        data = response.get('Items', [])  
        return data
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return []

# Streamlit UI to display data
st.title("PERFORMERS' SCORES")

data = fetch_all_data()  

if data:
   
    mapped_data = map_columns_with_final_score(data)
    st.dataframe(mapped_data)  
else:
    st.warning("No data found in the DynamoDB table.")


if "last_ran" not in st.session_state:
    st.session_state["last_ran"] = time.time()


if time.time() - st.session_state["last_ran"] > 60:
    st.session_state["last_ran"] = time.time()
    st.experimental_rerun()  
