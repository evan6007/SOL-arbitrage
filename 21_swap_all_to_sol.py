import requests
import base64
import json
import time
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solders import message
from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.rpc.commitment import Processed

RPC_URL = "https://mainnet.helius-rpc.com/?api-key=58c1de7e-a524-4b14-8472-eeec0e39d633"
QUOTE_API = "https://quote-api.jup.ag/v6/quote"
SWAP_API = "https://quote-api.jup.ag/v6/swap"
LAMPORTS = 1_000_000_000

SOL = "So11111111111111111111111111111111111111112"
USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

with open("keypair_old2.json", "r") as f:
    keypair = Keypair.from_json(json.load(f))
wallet_address = str(keypair.pubkey())
client = Client(RPC_URL)

def get_token_balance(wallet: str, mint: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenAccountsByOwner",
        "params": [
            wallet,
            {"mint": mint},
            {"encoding": "jsonParsed"}
        ]
    }
    res = requests.post(RPC_URL, json=payload)
    res.raise_for_status()
    accounts = res.json()["result"]["value"]
    if not accounts:
        return 0.0
    amount = accounts[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
    return float(amount)

def get_quote(input_mint, output_mint, amount, decimals=6):
    params = {
        "inputMint": input_mint,
        "outputMint": output_mint,
        "amount": str(int(amount * (10 ** decimals))),
        "slippageBps": 30,
        "onlyDirectRoutes": "false"
    }
    res = requests.get(QUOTE_API, params=params)
    if not res.ok:
        print(f"❌ quote 錯誤: {res.text}")
        return None
    return res.json()

def swap(quote, wrap_sol):
    payload = {
        "quoteResponse": quote,
        "userPublicKey": wallet_address,
        "wrapUnwrapSOL": wrap_sol
    }
    res = requests.post(SWAP_API, json=payload)
    if not res.ok or "swapTransaction" not in res.json():
        print(f"❌ swap 錯誤: {res.text}")
        return
    tx_b64 = res.json()["swapTransaction"]
    raw_tx = VersionedTransaction.from_bytes(base64.b64decode(tx_b64))
    sig = keypair.sign_message(message.to_bytes_versioned(raw_tx.message))
    signed_tx = VersionedTransaction.populate(raw_tx.message, [sig])
    result = client.send_raw_transaction(txn=bytes(signed_tx), opts=TxOpts(skip_preflight=False, preflight_commitment=Processed))
    tx_sig = json.loads(result.to_json())["result"]
    print(f"✅ 交易送出成功: https://solscan.io/tx/{tx_sig}")

def swap_all_to_sol():
    for token_mint, name in [(USDC, "USDC"), (USDT, "USDT")]:
        balance = get_token_balance(wallet_address, token_mint)
        if balance < 0.001:
            print(f"💤 {name} 餘額不足，跳過")
            continue
        print(f"🔁 嘗試把 {balance:.6f} {name} 換回 SOL")
        quote = get_quote(token_mint, SOL, balance, decimals=6)
        if quote:
            swap(quote, wrap_sol=True)
            time.sleep(10)

if __name__ == "__main__":
    swap_all_to_sol()
