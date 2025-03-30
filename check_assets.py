import json
import requests
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solana.rpc.api import Client

# === 設定 ===
RPC_URL = "https://mainnet.helius-rpc.com/?api-key=58c1de7e-a524-4b14-8472-eeec0e39d633"
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

# === 讀取 keypair.json，取得地址與 pubkey ===
with open("keypair_old2.json", "r") as f:
    keypair = Keypair.from_json(json.load(f))

wallet_pubkey = keypair.pubkey()               # For get_balance()
wallet_address = str(wallet_pubkey)            # For token query

# === 查詢 SOL 餘額 ===
sol_client = Client(RPC_URL)
sol_balance_lamports = sol_client.get_balance(wallet_pubkey).value
sol_balance = sol_balance_lamports / 1_000_000_000
print(f"🪙 SOL 餘額：{sol_balance:.6f} SOL")

# === 查詢 Token 餘額通用函式 ===
def get_token_balance(mint_address: str) -> float:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet_address,
            {"mint": mint_address},
            {"encoding": "jsonParsed"}
        ]
    }
    try:
        res = requests.post(RPC_URL, json=payload).json()
        accounts = res.get("result", {}).get("value", [])
        if not accounts:
            return 0.0
        amount = accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
        return float(amount)
    except:
        return 0.0

# === 查詢 USDC 和 USDT 餘額 ===
usdc_balance = get_token_balance(USDC_MINT)
usdt_balance = get_token_balance(USDT_MINT)

print(f"💵 USDC 餘額：{usdc_balance:.6f} USDC")
print(f"💴 USDT 餘額：{usdt_balance:.6f} USDT")
