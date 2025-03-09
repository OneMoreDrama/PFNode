import requests
import pandas as pd
import xrpl
import json
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
import xrpl.transaction
from xrpl.models.transactions import Payment, Memo
from xrpl.utils import str_to_hex
import pyodbc
from collections import defaultdict
import time
from datetime import datetime, timedelta
from openai import OpenAI
import Settings as s
import CommonFunction as cf
import BlockchainDataIncremental


# Load all transactions from the XRP Ledger for specific node addresses
# Save the transactions to the staging table for the database level processing
def LoadTransactionsFull():
    
    NodeList = cf.ExecuteSQLQuery('SELECT [NodeHashKey],[Address],[Name] FROM [PFNode].[pfn].[tbl_Node] WHERE TransactionLoadingFlag=1')



    for Node in NodeList:

        HasMore = True 
        Marker = None
        while HasMore:
            if Marker is None:
                Payload = json.dumps({
                "method": "account_tx",
                "params": [{
                    "account": Node.Address,
                    "binary": False,
                    "forward": False,
                    "ledger_index_max": -1,
                    "ledger_index_min": -1,
                    "limit": 100}],
                "id": 1,
                "jsonrpc": "2.0"})
            else:
                Payload = json.dumps({
                "method": "account_tx",
                "params": [{
                    "account": Node.Address,
                    "binary": False,
                    "forward": False,
                    "ledger_index_max": -1,
                    "ledger_index_min": -1,
                    "limit": 100,
                    "marker": Marker}],
                "id": 1,
                "jsonrpc": "2.0"})

            Headers = {'Content-Type': 'application/json'}
            
            Response = requests.request("POST", s.BCNodeURL, headers=Headers, data=Payload)
            Response = Response.json()
            if "marker" in Response["result"]:
                Marker = Response["result"]["marker"]
            else:
                Marker = None
            HasMore = Marker is not None
        
        
            for Tran in Response["result"]["transactions"]:
                Timestamp = datetime(2000, 1, 1) + timedelta(seconds=Tran["tx"]["date"])
                Hash = Tran["tx"].get('hash')
                FromAddress = Tran["tx"].get('Account')
                ToAddress = Tran["tx"].get('Destination')
                if isinstance(Tran["tx"].get('Amount'), str):
                    Amount = int(Tran["tx"].get('Amount')) / 1000000  
                    Currency = 'XRP'
                elif "Amount" in Tran["tx"]:
                    Amount = Tran["tx"]["Amount"].get('value')
                    Currency = Tran["tx"]["Amount"].get('currency')                                           
                if ("Memos" in Tran["tx"]):
                    Memo = bytes.fromhex(Tran["tx"]["Memos"][0]["Memo"]["MemoData"]).decode("utf-8")
                else:
                    Memo = ''
                
            
                Cursor = Connection.cursor()
                Cursor.execute("INSERT stg.tbl_Transaction ([Timestamp], [Hash], [FromAddress], [ToAddress], [Currency], [Amount], [Memo]) VALUES(?, ?, ?, ?, ?, ?, ?)", 
                            (Timestamp, Hash, FromAddress, ToAddress, Currency, Amount, Memo))
                Connection.commit()
                Cursor.close()
            

    Connection.close() 


def LoadAddresses():
    BlockchainDataIncremental.LoadAddresses()

def LoadGoogleDocumentTransactionMapping():
    BlockchainDataIncremental.LoadGoogleDocumentTransactionMapping()

if __name__ == "__main__":
    LoadTransactionsFull()
    LoadAddresses()
    LoadGoogleDocumentTransactionMapping()



