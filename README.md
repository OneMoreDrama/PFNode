# PFNode
Multi-node platform for Post Fiat



Nodes:

---------------------------------------------------------------------------------

**Forecaster** (Status: MVP) - an AI tool designed to assist users with data on any market listed on Polymarket

  Docs: https://docs.google.com/document/d/1J7RfZYZk0OYBE1-1Y8qk73jcegRLhojVxJu-G4NdExo/

---------------------------------------------------------------------------------

**PostFiat Buzz** (Status: development) - analytics and insights based on Post Fiat chain activity

---------------------------------------------------------------------------------

## File Descriptions

### Backend.py
Handles communication between users and the Flux API, processing user queries about Polymarket markets and delivering responses via XRP Ledger transactions.

### BlockchainDataFull.py
Performs full historical data loading from the XRP Ledger for specified node addresses, storing transaction data in the database for further processing.

### BlockchainDataIncremental.py
Handles incremental loading of recent transactions from the XRP Ledger, updating user information and messages in the database.

### CommonFunction.py
Contains utility functions used across the application, including database operations and event logging.

### DiscordFrontend.py
Implements a Discord bot interface for the Forecaster node, allowing users to interact with the system through Discord messages and commands.

### Embedding.py
Processes chats between task node and users into vector embeddings using OpenAI's embedding models and stores them in a Milvus vector database for semantic search capabilities. Only for Buzz node

### GoogleDocument.py
Retrieves and stores Google Documents referenced in XRP Ledger transactions. Only for Buzz node

### Settings.py
Centralizes configuration settings for the application, including database connections, API endpoints, and blockchain node information.


