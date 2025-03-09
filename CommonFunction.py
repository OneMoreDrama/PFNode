import pyodbc
import Settings as s

Connection = None

def ExecuteSQLQuery(SQLQuery, Parameters=None):
    global Connection
    if Connection is None:
        Connection = pyodbc.connect(s.DB.ConnectionString())
    Cursor = Connection.cursor()
    if Parameters is None:
        Cursor.execute(SQLQuery)
    else:
        Cursor.execute(SQLQuery, Parameters)

    if Cursor.description is not None:
        Result = Cursor.fetchall()
    else:
        Result = None

    Cursor.close()
    Connection.commit()

    return Result

    

def EventLog(Source,Type,Name,Description,Data):
    print(Source,Type,Name,Description)
    JoinedData = '---------'.join(Data)
    ExecuteSQLQuery("INSERT INTO [dbo].[tbl_EventLog] ([Source],Type,[Name],[Description],[Data]) VALUES(?,?,?,?,?)", (Source,Type,Name,Description,JoinedData))
    return

def Exit():
    if Connection is not None:
        Connection.close()
    return