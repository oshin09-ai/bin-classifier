from datetime import datetime
from elasticsearch import Elasticsearch
import json

# Initialize Elasticsearch client with environment variables
import os

ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL')
ELASTICSEARCH_API_KEY = os.environ.get('ELASTICSEARCH_API_KEY')

if not ELASTICSEARCH_URL or not ELASTICSEARCH_API_KEY:
    print("Warning: Missing Elasticsearch credentials")
    es = None
else:
    es = Elasticsearch(
        ELASTICSEARCH_URL,
        api_key=ELASTICSEARCH_API_KEY,
        verify_certs=False,  # For development environment
        ssl_show_warn=False,
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=3
    )

# Verify connection
try:
    if not es.ping():
        raise ValueError("Connection to Elasticsearch failed")
except Exception as e:
    print(f"Failed to connect to Elasticsearch: {str(e)}")
    es = None

class RecyclingResult:
    INDEX_NAME = "bin_classifications"

    @staticmethod
    def init_index():
        """Initialize the Elasticsearch index with mapping"""
        if not es:
            print("Warning: Elasticsearch client is not initialized")
            return
            
        try:
            # First check if we can access the cluster
            if not es.ping():
                raise ConnectionError("Cannot connect to Elasticsearch")
                
            # Check if index exists
            if not es.indices.exists(index=RecyclingResult.INDEX_NAME):
                try:
                    mapping = {
                        "settings": {
                            "number_of_shards": 1,
                            "number_of_replicas": 0
                        },
                        "mappings": {
                            "properties": {
                                "product_description": {"type": "text"},
                                "classification_result": {
                                    "type": "text",
                                    "index": False
                                },
                                "created_at": {"type": "date"}
                            }
                        }
                    }
                    es.indices.create(index=RecyclingResult.INDEX_NAME, body=mapping)
                    print(f"Successfully created index: {RecyclingResult.INDEX_NAME}")
                except Exception as create_error:
                    if "resource_already_exists_exception" in str(create_error):
                        print(f"Index {RecyclingResult.INDEX_NAME} already exists")
                    else:
                        print(f"Failed to create index: {str(create_error)}")
            else:
                print(f"Index {RecyclingResult.INDEX_NAME} already exists")
                
        except Exception as e:
            print(f"Elasticsearch initialization error: {str(e)}")

    @staticmethod
    def save(product_description, classification_result):
        """Save a recycling result to Elasticsearch"""
        if not es:
            print("Warning: Elasticsearch is not available, skipping save operation")
            return None
            
        doc = {
            'product_description': product_description,
            'classification_result': json.dumps(classification_result),
            'created_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Try to create the index if it doesn't exist
            if not es.indices.exists(index=RecyclingResult.INDEX_NAME):
                RecyclingResult.init_index()
            
            # Attempt to save the document
            response = es.index(index=RecyclingResult.INDEX_NAME, document=doc)
            print(f"Successfully saved document with ID: {response['_id']}")
            return response['_id']
            
        except Exception as e:
            error_message = str(e)
            if "AuthorizationException" in error_message:
                print("Warning: Insufficient permissions to save to Elasticsearch")
                return None
            else:
                print(f"Warning: Failed to save to Elasticsearch: {error_message}")
                return None

    @staticmethod
    def get_latest():
        """Get the most recent classification result"""
        if not es:
            print("Warning: Elasticsearch is not available")
            return None
            
        try:
            result = es.search(
                index=RecyclingResult.INDEX_NAME,
                body={
                    "query": {"match_all": {}},
                    "sort": [{"created_at": {"order": "desc"}}],
                    "size": 1
                }
            )
            hits = result.get('hits', {}).get('hits', [])
            if hits:
                return hits[0]['_source']
        except Exception as e:
            error_message = str(e)
            if "index_not_found_exception" in error_message:
                print("Warning: No classification results found")
            elif "AuthorizationException" in error_message:
                print("Warning: Insufficient permissions to read from Elasticsearch")
            else:
                print(f"Warning: Failed to retrieve results: {error_message}")
        return None
