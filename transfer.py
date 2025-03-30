from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solana.rpc.api import Client
import json

# 固定參數
SOURCE_KEYPAIR_FILE = "64_wallet.json"
DESTINATION_ADDRESS = "fm9dkWcNprg5WKb7V2apCWQ6xmE73fodz6D5DFmth5K"
AMOUNT_SOL = 0.1
RPC_URL = "https://api.mainnet-beta.solana.com"

# 載入私鑰
with open(SOURCE_KEYPAIR_FILE, "r") as f:
    key_data = json.load(f)
    sender = Keypair.from_bytes(bytes(key_data["account"]))

client = Client(RPC_URL)

# 查餘額
balance = client.get_balance(sender.pubkey()).value / 1e9
print(f"來源地址: {sender.pubkey()}")
print(f"目前餘額: {balance:.4f} SOL")

if balance < AMOUNT_SOL:
    raise Exception("❌ 餘額不足")

# 建立轉帳交易
lamports = int(AMOUNT_SOL * 1e9)
destination = Pubkey.from_string(DESTINATION_ADDRESS)
blockhash = client.get_latest_blockhash().value.blockhash

ix = transfer(
    TransferParams(
        from_pubkey=sender.pubkey(),
        to_pubkey=destination,
        lamports=lamports,
    )
)

# 建立並簽名交易
tx = Transaction.new_signed_with_payer(
    instructions=[ix],
    payer=sender.pubkey(),
    signing_keypairs=[sender],
    recent_blockhash=blockhash,
)

# 發送交易
tx_bytes = bytes(tx)
resp = client.send_raw_transaction(tx_bytes)
print(f"✅ 已發送交易: {resp.value}")
print(f"🔗 https://solscan.io/tx/{resp.value}")
