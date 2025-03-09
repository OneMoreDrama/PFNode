import requests
import pyodbc
import settings as s

def DownloadGoogleDocument(DocumentID, ExportFormat='txt'):
    URL = f"https://docs.google.com/document/d/{DocumentID}/export?format={ExportFormat}"
    Responce = requests.get(URL)
    Responce = Responce.text
    Connection = pyodbc.connect(s.DB.ConnectionString())  
    Cursor = Connection.cursor()
    
    Query = 'INSERT [PFNode].[stg].[tbl_GoogleDocument] ([ID], [Text]) VALUES(?, ?)' 
    Cursor.execute(Query, (DocumentID, Responce))
    Connection.commit()
    Cursor.close()
    Connection.close()

if __name__ == "__main__":

    Connection = pyodbc.connect(s.DB.ConnectionString())  
    Cursor = Connection.cursor()
    Query = 'SELECT DISTINCT [GoogleDocumentID] FROM [PFNode].[pfn].[tbl_GoogleDocumentTransactionMapping]' 
    Cursor.execute(Query)
    GoogleDocumentList = Cursor.fetchall()  
    Cursor.close()
    Connection.close()
    for GoogleDocument in GoogleDocumentList:
        DownloadGoogleDocument(GoogleDocument.GoogleDocumentID)