from dotenv import load_dotenv
import os

load_dotenv()

class DB:
    DRIVER='ODBC Driver 17 for SQL Server'
    SERVER=os.getenv("SERVER")
    DATABASE=os.getenv("DATABASE")
    UID=os.getenv("UID")
    PASSWORD=os.getenv("PASSWORD")

    @classmethod
    def ConnectionString(cls):
        return (
            f"DRIVER={{{cls.DRIVER}}};"
            f"SERVER={cls.SERVER};"
            f"DATABASE={cls.DATABASE};"
            f"UID={cls.UID};"
            f"PWD={cls.PASSWORD}")


FluxURLGenerate = "https://rocket-xbt-syndication-d1b604b2465d.herokuapp.com/api/generate/"#"https://api.userocket.app/api/generate/"
FluxURLChat = "https://rocket-xbt-syndication-d1b604b2465d.herokuapp.com/api/chat/"

BCNodeURL = os.getenv("BCNodeURL")

PolyMarketForecasterNodeAddress=os.getenv("PolyMarketForecasterNodeAddress")
PolyMarketForecasterNodeSeed=os.getenv("PolyMarketForecasterNodeSeed")
PolyMarketForecasterNodeKey = os.getenv("PolyMarketForecasterNodeKey")

StartTimestamp = "'2025-03-06'"

DiscordAppToken = os.getenv("DiscordAppToken")

ChatGPTApiKey=os.getenv("ChatGPTApiKey")

DiscordWelcomeMessage="""Hello, I’m Forecaster, your data-driven assistant for any Polymarket market—though I’m especially effective with political and long-dated prediction markets. By automating research and filtering out biases, I deliver only factual insights to reduce your cognitive load and help avoid emotionally driven mistakes or oversights. Unlike influencers, I’m purely objective, analyzing a wide range of data to ensure you have all the information you need before making a decision.

Note: To receive a response right now, please ask your question about any prediction market in your first prompt. If you see an “event-not-found” message, just use the reset_context command and try again. Let’s begin!""" 


