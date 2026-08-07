"""Resolve exact Saxo SIM stock instruments without modifying ETF mappings."""
import requests
from quant_ai_trader.config.settings import SaxoSettings
from quant_ai_trader.workflows.stocks.universe import US_STOCK_UNIVERSE


def run(settings=None):
    settings=settings or SaxoSettings.from_environment()
    session=requests.Session(); session.headers.update({"Authorization":f"Bearer {settings.access_token}"})
    resolved={}; missing=[]
    for symbol in US_STOCK_UNIVERSE:
        response=session.get(f"{settings.base_url}/ref/v1/instruments",params={"AssetTypes":"Stock","Keywords":symbol,"$top":20},timeout=30)
        response.raise_for_status()
        matches=[x for x in response.json().get("Data",[]) if x.get("Symbol","").split(":")[0].upper()==symbol]
        us=[x for x in matches if x.get("Symbol","").lower().endswith((":xnas",":xnys",":arcx"))]
        choice=(us or matches or [None])[0]
        if choice is None: missing.append(symbol); continue
        resolved[symbol]={"uic":int(choice["Identifier"]),"asset_type":str(choice["AssetType"]),"symbol":choice.get("Symbol")}
    return {"resolved":resolved,"missing":missing,"all_resolved":not missing}


if __name__=="__main__":
    result=run(); print({"resolved_count":len(result["resolved"]),"missing":result["missing"],"all_resolved":result["all_resolved"]})
