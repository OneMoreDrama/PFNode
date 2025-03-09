import requests
import xrpl
import json
from xrpl.wallet import Wallet
from xrpl.clients import JsonRpcClient
import xrpl.transaction
from xrpl.models.transactions import Payment, Memo
from xrpl.utils import str_to_hex
import time
import Settings as s
import CommonFunction as cf
import traceback

#Get new messages from the database and send them to the Flux API
def Asking():

    Messages=cf.ExecuteSQLQuery(f"""SELECT m.MessageKey, m.Role, m.Text, m.FluxChatID, u.UserKey, u.Address, m.Mode, uns.NodeKey
                FROM pfn.tbl_Message m
                INNER JOIN pfn.tbl_User u ON u.UserKey=m.UserKey
				LEFT JOIN pfn.tbl_UserNodeSetting uns ON uns.NodeKey=m.NodeKey AND uns.UserKey=m.UserKey
                WHERE m.Status='Created' AND m.Type='Asking' AND m.Timestamp>={s.StartTimestamp}
                ORDER BY m.Timestamp""")
  
    for Message in Messages:
        try:
            Response = None
            if Message.Mode == 'Full' or Message.Mode == 'Full with research':
                LightMode=False
            else:
                LightMode=True

            if Message.FluxChatID is None:
                Payload = {"prompt": Message.Text, "lightMode": LightMode}
            else:
                Payload = {"prompt": Message.Text, "chatId": Message.FluxChatID, "lightMode": LightMode}
            
            Headers = {"Content-Type": "application/json","Authorization":"AURI_OS82CI7H4V80B9PKBIXQ74WS"}
            Response = requests.post(s.FluxURLGenerate, json=Payload, headers=Headers)
            Response = Response.json()
            if Message.FluxChatID is None:
                Message.FluxChatID = Response['chatId']
                
                cf.ExecuteSQLQuery(f"UPDATE pfn.tbl_UserNodeSetting SET CurrentFluxChatID=? WHERE UserKey= ? AND NodeKey= ?", (Message.FluxChatID, Message.UserKey, Message.NodeKey))
                
                cf.ExecuteSQLQuery(f"UPDATE pfn.tbl_Message SET FluxChatID=? WHERE MessageKey= ?", (Message.FluxChatID, Message.MessageKey))

            
    
            cf.ExecuteSQLQuery("UPDATE pfn.tbl_Message SET Status='Processing' WHERE MessageKey= ?", (Message.MessageKey))
        except Exception:
            cf.EventLog('Backend.py','Exception','Asking',traceback.format_exc(),str(Response))
            cf.ExecuteSQLQuery("UPDATE pfn.tbl_Message SET Status='Error' WHERE MessageKey= ?", (Message.MessageKey))



            
#Get answers from the Flux API and send them to the users via the XRP Ledger
def Answering():
  
    payload = json.dumps({
      "method": "account_tx",
      "params": [
        {
          "account": s.PolyMarketForecasterNodeAddress,
          "binary": False,
          "forward": False,
          "ledger_index_max": -1,
          "ledger_index_min": -1,
          "limit": 1000
        }
      ],
      "id": 1,
      "jsonrpc": "2.0"
    })
    headers = {
      'Content-Type': 'application/json'
    }
    client = JsonRpcClient(s.BCNodeURL)
    wallet = Wallet.from_secret(s.PolyMarketForecasterNodeSeed)

    Messages =cf.ExecuteSQLQuery("""SELECT m.MessageKey, m.Role, m.Text, m.FluxChatID, u.UserKey, u.Address, m.Mode, uns.NodeKey
                FROM pfn.tbl_Message m
                INNER JOIN pfn.tbl_User u ON u.UserKey=m.UserKey
				LEFT JOIN pfn.tbl_UserNodeSetting uns ON uns.NodeKey=m.NodeKey AND uns.UserKey=m.UserKey
                WHERE m.Status='Processing' AND m.Type='Asking'
                ORDER BY m.Timestamp""")

    for Message in Messages:
        try:
            Response = None
            AnswerText = None
            URL = f"{s.FluxURLChat}{Message.FluxChatID}"
            Headers = {"Accept": "application/json","Authorization":"AURI_OS82CI7H4V80B9PKBIXQ74WS"}
            Response = requests.get(URL, headers=Headers)
            Response = Response.json()
            if Response.get('inProgress') == False:
                if 'error' in Response:
                    AnswerText = Response['error']
                else:  
                    if Message.Mode == 'Full with research':
                        Report = f'\n\n FULL RESEARCH: \n\n {Response["report"]}'
                    else:
                        Report = ''
                    AnswerText = f'Market: https://polymarket.com/event/{Response["eventSlug"]}   {Response["messages"][len(Response['messages'])-1]}    {Report}' 
            elif Response.get('message') == 'Chat Not Found':
                cf.ExecuteSQLQuery(f"UPDATE pfn.tbl_Message SET FluxChatID=NULL, Status='Created' WHERE MessageKey= ?", (Message.MessageKey))
                cf.ExecuteSQLQuery(f"UPDATE pfn.tbl_UserNodeSetting SET CurrentFluxChatID=NULL WHERE UserKey= ? AND NodeKey= ?", ( Message.UserKey, Message.NodeKey))
            
            
        except:
            AnswerText = 'Agent conversation exception'
            cf.EventLog('Backend.py','Exception','Answering Flux API second call',traceback.format_exc(),str(Response))
            cf.ExecuteSQLQuery("UPDATE pfn.tbl_Message SET Status='Error' WHERE MessageKey= ?", (Message.MessageKey))
 
        
            
        if AnswerText is not None:
            try:
                RPLResponse = None
                for StartIndex in range(0, len(AnswerText), 1000):
                    StringPart = AnswerText[StartIndex:StartIndex+1000] 
                    payment = Payment(
                        account=wallet.address,
                        amount="1",
                        destination=Message.Address,
                        memos=[Memo(memo_data=str_to_hex(StringPart))]
                    )
                    
                    RPLResponse = xrpl.transaction.submit_and_wait(payment, client, wallet)
                    cf.ExecuteSQLQuery("{CALL [pfn].[sp_NewAnsweringMessage] (?, ?, ?, ?, ?, ?)}", (Message.Address,RPLResponse.result["hash"],StringPart,Message.FluxChatID, Message.UserKey, Message.NodeKey))
            
                cf.ExecuteSQLQuery("UPDATE pfn.tbl_Message SET Status='Processed' WHERE MessageKey= ?", (Message.MessageKey))
            except:
                cf.EventLog('Backend.py','Exception','Answering transaction sending',traceback.format_exc(),str(RPLResponse))
                cf.ExecuteSQLQuery("UPDATE pfn.tbl_Message SET Status='Error' WHERE MessageKey= ?", (Message.MessageKey))
            
    
if __name__ == "__main__":
    Asking()
    Answering()