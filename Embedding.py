import os
import pyodbc
from openai import OpenAI
from pymilvus import connections, FieldSchema, CollectionSchema, DataType,Collection, utility
import Settings as s


LLMClient=OpenAI(api_key=s.ChatGPTApiKey)
 
EMBED_MODEL = "text-embedding-3-large"   # or another supported model
EMBED_DIM = 1536                         # for 'text-embedding-ada-002'

# Milvus
MILVUS_HOST = "localhost"    # Replace if needed
MILVUS_PORT = "19530"
COLLECTION_NAME = "chat_collection"  # Name of the collection in Milvus


def GetEmbedding(text, model="text-embedding-3-large"):
    response = LLMClient.embeddings.create(input=[text], model=model)
    embedding = response.data[0].embedding
    return embedding


def ChunkText(text, chunk_size=500, overlap=50):
    """
    Splits text into chunks of `chunk_size` tokens, with each chunk overlapping
    the previous chunk by `overlap` tokens.

    Parameters:
        text (str): The input text to be chunked.
        chunk_size (int): The number of tokens per chunk.
        overlap (int): The number of tokens to overlap between consecutive chunks.

    Returns:
        List[str]: A list of text chunks.
    """
    # For simplicity, we use whitespace to split tokens.
    #if chunk_size + 50 < len(text.split()):
    #    chunk_size = len(text.split())
    tokens = text.split()
    chunks = []
    start = 0

    # Process tokens until we reach the end of the token list.
    while start < len(tokens):
        # Grab a chunk of tokens.
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk = " ".join(chunk_tokens)
        chunks.append(chunk)
        # If we've reached or passed the end of tokens, stop.
        if end >= len(tokens):
            break

        # Move start forward by chunk_size minus the overlap.
        start += chunk_size - overlap

    return chunks

###############################
# MAIN SCRIPT
###############################

def main():

    Connection = pyodbc.connect(s.DB.ConnectionString())
    Cursor = Connection.cursor()
    Query = 'SELECT master.dbo.fn_varbintohexstr([ChatDocumentHashKey]) AS ChatDocumentHashKey, [Text] FROM [PFNode].[pfn].[tbl_ChatDocument]' 
    Cursor.execute(Query)
    Result = Cursor.fetchall()  
    Cursor.close()
    Connection.close()


    ChatDocumentList = []
    for Row in Result:
        # row is a pyodbc.Row (read-only)
        data = {
            'ChatDocumentHashKey': Row.ChatDocumentHashKey,  # or row[0]
            'Text': Row.Text,                                # or row[1]
        }
        # Now you can add new fields:
        data['Chunks'] = ChunkText(data['Text'])
        ChatDocumentList.append(data)
    a=0
    b=0

    EmbeddingList = []
    for Doc in ChatDocumentList:
        DocID = Doc['ChatDocumentHashKey']
        a=a+1
        b=0
        for Chunk in Doc['Chunks']:
            b=b+1
            print('Doc ',a,' ID: ',DocID, ' TextLength: ',len(Doc['Text']), ' Chunks: ',b,'/',len(Doc['Chunks']))
            Embedding = GetEmbedding(Chunk)
            EmbeddingList.append({"ID": DocID, "Embedding": Embedding, "Text": Chunk})


    # Connect to Milvus
    connections.connect("default", host="localhost", port="19530")

    # Define the schema: an ID field and a vector field
    FieldList = [
        FieldSchema(name="ID", dtype=DataType.VARCHAR, is_primary=True, auto_id=False, max_length=36),
        FieldSchema(name="Embedding", dtype=DataType.FLOAT_VECTOR, dim=len(EmbeddingList[0]["Embedding"])),
        FieldSchema(name="Text", dtype=DataType.VARCHAR, max_length=65535)
    ]
    Schema = CollectionSchema(FieldList, description="Chat Documents")

    # Create (or load) collection
    collection = Collection("ChatDocument", Schema)
    # (Optional: create an index on the vector field)
    index_params = {"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}}
    collection.create_index(field_name="Embedding", index_params=index_params)

    # Prepare data for insertion
    ids = [str(doc["ID"]) for doc in EmbeddingList]
    embeddings = [doc["Embedding"] for doc in EmbeddingList]
    texts = [doc["Text"] for doc in EmbeddingList]

    # Insert data
    MR = collection.insert([ids, embeddings, texts])
    collection.flush()

if __name__ == "__main__":
    main()
