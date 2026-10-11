"""Metrika: coleta opcional de métricas públicas de artistas do Spotify."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

URL = "https://metrika.run/api/v1/resources/search"

def parse_data(payload, ids):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("Formato da resposta desconhecido")
    lookup = {v:k for k,v in ids.items()}
    output = {}
    for item in payload["data"]:
        if not isinstance(item, dict) or item.get("platform") != "spotify" or item.get("type") != "account":
            continue
        key = lookup.get(item.get("identifier"))
        if not key or item.get("status") != "available":
            continue
        metrics = item.get("metrics") or {}
        extracted = {}
        for field, dest in (("followers","followers"),("views","monthlyListeners")):
            info = metrics.get(field)
            if not isinstance(info, dict) or info.get("status") != "available":
                continue
            semantic = str(info.get("semantic","")).lower().strip().replace("_"," ").replace("-"," ")
            if field == "views" and semantic not in ("monthly listeners","monthly listener"):
                continue
            if field == "followers" and semantic not in ("followers","spotify followers"):
                continue
            value = info.get("value")
            if isinstance(value, bool) or not isinstance(value, int) or not (100000 <= value <= 200000000):
                continue
            raw = info.get("collected_at")
            if not isinstance(raw, str):
                continue
            try:
                time = datetime.fromisoformat(raw.replace("Z","+00:00"))
            except ValueError:
                continue
            if time.tzinfo is None:
                continue
            date = time.astimezone(ZoneInfo("America/Cuiaba")).date().isoformat()
            extracted[dest] = dict(value=value,date=date,source="Metrika (Spotify)",approximate=False,collectedAt=raw)
        if extracted:
            output[key] = extracted
    return output

def collect(ids):
    token = os.getenv("METRIKA_API_TOKEN","").strip()
    if not token:
        return None
    request = {"resources":[{"platform":"spotify","type":"account","identifier":aid} for aid in ids.values()]}
    response = requests.post(URL,json=request,headers={"Authorization":"Bearer "+token},timeout=35)
    response.raise_for_status()
    return parse_data(response.json(),ids)

if __name__ == "__main__":
    sample = {"data":[{"platform":"spotify","type":"account","identifier":"123","status":"available","metrics":{
       "followers":{"value":61226773,"status":"available","collected_at":"2026-10-11T16:10:00Z","semantic":"followers"},
       "views":{"value":19028664,"status":"available","collected_at":"2026-10-11T16:10:00Z","semantic":"monthly listeners"}}}]}
    result = parse_data(sample,{"blackpink":"123"})
    assert result["blackpink"]["followers"]["value"] == 61226773
    assert result["blackpink"]["monthlyListeners"]["date"] == "2026-10-11"
    print("Teste Metrika aprovado")
