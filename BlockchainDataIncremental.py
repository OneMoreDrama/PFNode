import requests
import json
from xrpl.models.transactions import Payment, Memo
from datetime import datetime, timedelta
import Settings as s
import CommonFunction as cf

# Load last 100 transactions from the XRP Ledger for specific node addresses
# Save the transactions to the staging table for the database level processing
def LoadTransactionsIncremental():
    try:
        
        NodeList = cf.ExecuteSQLQuery('SELECT [NodeKey],[Address],[Name] FROM [pfn].[tbl_Node] WHERE TransactionLoadingFlag=1')

        cf.ExecuteSQLQuery('TRUNCATE TABLE stg.tbl_Transaction')

        for Node in NodeList:
            
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
            Headers = {'Content-Type': 'application/json'}
            
            Response = requests.request("POST", s.BCNodeURL, headers=Headers, data=Payload)
            Response = Response.json()
            
            
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

                cf.ExecuteSQLQuery("INSERT stg.tbl_Transaction ([Timestamp], [Hash], [FromAddress], [ToAddress], [Currency], [Amount], [Memo]) VALUES(?, ?, ?, ?, ?, ?, ?)", 
                            (Timestamp, Hash, FromAddress, ToAddress, Currency, Amount, Memo))
                
            cf.ExecuteSQLQuery('{CALL [pfn].[sp_Transaction]}')

    except Exception:
        cf.EventLog('BlockchainDataIncremental.py','Exception','LoadTransactionsIncremental',str(Exception),'')
   


#Find the Google Document ID from the transaction memo (need only for Buzz node, for data feed about the task node)
#Save the mapping to the database
def LoadGoogleDocumentTransactionMapping():
    try:
        cf.ExecuteSQLQuery('{CALL pfn.sp_GoogleDocumentTransactionMapping()}')
    except Exception:
        cf.EventLog('BlockchainDataIncremental.py','Exception','LoadGoogleDocumentTransactionMapping',str(Exception),'')


#Load the users from the transactions to the database
def LoadUsersFromTransactions():
    try:
        cf.ExecuteSQLQuery('{CALL pfn.sp_User()}')
    except Exception:
        cf.EventLog('BlockchainDataIncremental.py','Exception','LoadUsersFromTransactions',str(Exception),'')

#Create messages from the transaction memos
def LoadMessagesFromTransactions():
    try:
        cf.ExecuteSQLQuery('{CALL pfn.sp_Message()}')
    except Exception:
        cf.EventLog('BlockchainDataIncremental.py','Exception','LoadMessagesFromTransactions',str(Exception),'')


if __name__ == "__main__":
    LoadTransactionsIncremental()
    LoadUsersFromTransactions()
    LoadMessagesFromTransactions()
#    LoadGoogleDocumentTransactionMapping()
    cf.Exit()



