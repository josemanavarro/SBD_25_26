import os
import time
import json
import uuid
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

# ------------------ Configuración por entorno ------------------
BROKER_HOST = os.getenv("BROKER_HOST", "mosquitto")
BROKER_PORT = int(os.getenv("BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_QOS = int(os.getenv("MQTT_QOS", "0"))
MQTT_RETAIN = os.getenv("MQTT_RETAIN", "false").lower() == "true"

# Plantilla de topic: p.ej. coingecko/BTC, coingecko/ETH
TOPIC_TEMPLATE = os.getenv("TOPIC_TEMPLATE", "coingecko/{symbol}")

# Monedas (CoinGecko IDs, no tickers): "bitcoin,ethereum,cardano"
COINS = os.getenv("COINS", "bitcoin,ethereum")
# Divisa de referencia
FIAT = os.getenv("FIAT", "eur")

# Frecuencia de consulta (segundos)
INTERVAL_SECONDS = int(os.getenv("INTERVAL_SECONDS", "30"))

# Base URL (público) y opción PRO/DEMO
CG_BASE_URL = os.getenv("CG_BASE_URL", "https://api.coingecko.com/api/v3")
CG_API_KEY = os.getenv("CG_API_KEY")  # opcional (Demo/Pro)
CG_TIMEOUT = float(os.getenv("CG_TIMEOUT", "10.0"))

# Mapeo opcional id->símbolo para el topic (si no, usamos el id)
SYMBOL_MAP = json.loads(os.getenv("SYMBOL_MAP", "{}"))  # {"bitcoin":"BTC","ethereum":"ETH"}

# ------------------ Cliente MQTT ------------------
client_id = f"coingecko_publisher_{uuid.uuid4().hex[:8]}"
mqttc = mqtt.Client(client_id=client_id, clean_session=True)
if MQTT_USERNAME:
    mqttc.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqttc.connect(BROKER_HOST, BROKER_PORT)

# ------------------ Helper HTTP con reintentos ------------------
class Http429(Exception): pass

def _headers():
    h = {"Accept": "application/json"}
    if CG_API_KEY:
        # CoinGecko acepta cabecera x-cg-pro-api-key o query param, usamos header
        h["x-cg-pro-api-key"] = CG_API_KEY
    return h

@retry(
    retry=retry_if_exception_type((requests.RequestException, Http429)),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True
)
def fetch_prices(ids: str, fiat: str):
    url = f"{CG_BASE_URL}/simple/price"
    params = {"ids": ids, "vs_currencies": fiat, "include_market_cap": "false",
              "include_24hr_vol": "false", "include_24hr_change": "true", "precision": "full"}
    resp = requests.get(url, params=params, headers=_headers(), timeout=CG_TIMEOUT)
    # Manejo de rate limit
    if resp.status_code == 429:
        # Respetar Retry-After si existe
        retry_after = int(resp.headers.get("Retry-After", "0"))
        if retry_after > 0:
            time.sleep(retry_after)
        raise Http429(f"Rate limited by CoinGecko (429). Headers: {dict(resp.headers)}")
    resp.raise_for_status()
    return resp.json()

def now_iso():
    return datetime.now(timezone.utc).isoformat()

# ------------------ Loop principal ------------------
def main():
    ids = ",".join([c.strip() for c in COINS.split(",") if c.strip()])
    fiat = FIAT.strip().lower()

    if not ids:
        raise SystemExit("COINS no puede estar vacío.")

    print(f"[INIT] Broker: {BROKER_HOST}:{BROKER_PORT} | Coins: {ids} | Fiat: {fiat} | Interval: {INTERVAL_SECONDS}s")
    if CG_API_KEY:
        print("[INIT] Usando CoinGecko API key (Demo/Pro). Ajusta límites según tu plan.")

    while True:
        try:
            data = fetch_prices(ids, fiat)
            ts = now_iso()
            # data ej: {"bitcoin":{"eur":64932.12,"eur_24h_change":-0.32}, "ethereum":{...}}
            for coin_id, payload in data.items():
                symbol = SYMBOL_MAP.get(coin_id, coin_id)
                topic = TOPIC_TEMPLATE.format(symbol=symbol.upper(), id=coin_id.lower())
                message = {
                    "coin_id": coin_id,
                    "symbol": symbol.upper(),
                    "fiat": fiat.upper(),
                    "price": payload.get(fiat),
                    "change_24h": payload.get(f"{fiat}_24h_change"),
                    "source": "coingecko",
                    "timestamp": ts
                }
                mqttc.publish(topic, json.dumps(message), qos=MQTT_QOS, retain=MQTT_RETAIN)
                print(f"[MQTT] {topic} => {message}")
        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
