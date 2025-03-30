# === Quote 查詢 ===
def get_quote(input_mint, output_mint, amount):
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": str(amount),
            "slippageBps": int(SLIPPAGE * 10000),
            "onlyDirectRoutes": "false"
        }
        res = requests.get(QUOTE_API, params=params)
        return res.json() if res.ok else None
    except Exception as e:
        print(f"{e}",end="")
        return None

# === Token 餘額查詢 ===
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


def confirm_tx(tx_id, max_retries=1):
    retries = 0
    while retries < max_retries:
        try:
            confirmation = client.confirm_transaction(Signature.from_string(tx_id), commitment=Finalized)
            if confirmation.value:
                print("✅ 交易已最終確認（Finalized）")
                return True
            else:
                print("❌ 交易尚未最終確認，等待中...")
        except Exception as e:
            print(f"\n⚠️ 無法確認交易（第 {retries+1} 次）：{e}")
        
        retries += 1
        time.sleep(3)

    print(f"❌ 超過最大重試次數，交易 {tx_id} 無法確認")
    return False




def soltousdc(sol_to_use_lamports,sol_to_use):
    # Step 1: SOL → USDC
    to_do = True
    while to_do:
        time.sleep(2)
        try:
            
            intsol_to_use_lamports = int(sol_to_use_lamports)
            slippageBps = int(0.00001)  # 1% slippage
            q1 = requests.get(
                f"{QUOTE_API}?inputMint={SOL_MINT}&outputMint={USDC_MINT}&amount={intsol_to_use_lamports}&slippageBps={slippageBps}"
            ).json()

            # print("q1[outAmount]=", q1["outAmount"])

            q3 = get_quote(USDC_MINT, SOL_MINT, int(q1["outAmount"]))
            # print("q3[outAmount]=", q3["outAmount"])

            estimated_final_sol = int(q3["outAmount"]) / LAMPORTS
            simulated_profit = estimated_final_sol - sol_to_use
            simulated_profit_pct = (simulated_profit / sol_to_use) * 100

            THRESHOLD = 0.03
            if simulated_profit_pct < THRESHOLD:
                sys.stdout.write(f"\r🔁 Step 1: 預估利潤 {simulated_profit_pct:.4f}% 低於 {THRESHOLD}% 門檻")
                sys.stdout.flush()
                continue

            print(f"🪙 預估利潤 {simulated_profit_pct:.4f}% 高於 {THRESHOLD}% 門檻")
            print(f"🔍 預期獲得 USDC: {int(q1['outAmount']) / 1e6:.6f} USDC")

            payload_1 = {"quoteResponse": q1, "userPublicKey": wallet_address, "wrapUnwrapSOL": True}
            swap_1 = requests.post(SWAP_API, json=payload_1).json()
            signed_tx_1 = VersionedTransaction.populate(
                VersionedTransaction.from_bytes(base64.b64decode(swap_1["swapTransaction"])).message,
                [keypair.sign_message(message.to_bytes_versioned(
                    VersionedTransaction.from_bytes(base64.b64decode(swap_1["swapTransaction"])).message))]
            )
            tx_id_1 = json.loads(client.send_raw_transaction(
                txn=bytes(signed_tx_1), opts=TxOpts(skip_preflight=False, preflight_commitment=Processed) #本來skip pre 是false
            ).to_json())["result"]

            print(f"✅ SOL → USDC 交易送出成功：https://solscan.io/tx/{tx_id_1}")
            confirm_state = confirm_tx(tx_id_1)

            # ✅ 這裡加入防呆：確認 USDC 有成功收到
            for i in range(2):  # 最多查 5 次，避免陷入死循環
                time.sleep(2)
                usdc_balance = get_token_balance(USDC_MINT)
                print(f"📊 實際收到 USDc 數量：{usdc_balance:.6f} USDC")
                if usdc_balance > 1: #至少有一塊錢
                    to_do = False
                    return q1["outAmount"]
                print("⚠️ 檢查到 USDC 為 0，重新嘗試 Step 1...")


        except Exception as e:
            print(f"⚠️",end="")
            time.sleep(2)
        time.sleep(2)


def usdctosol(usdc_amount,sol_to_use,step1_overearn):
    #Step 3: USDc → SOL
    to_do = True
    while to_do:
        time.sleep(1)
        try:
            
            slippageBps = int(0.00001)  # 1% slippage
            q3 = requests.get(
                f"{QUOTE_API}?inputMint={USDC_MINT}&outputMint={SOL_MINT}&amount={usdc_amount}&slippageBps={slippageBps}"
            ).json()
            # print("q3[outAmount]=", q3["outAmount"])

            estimated_final_sol = int(q3["outAmount"]) / LAMPORTS
            simulated_profit = estimated_final_sol - sol_to_use
            simulated_profit_pct = (simulated_profit / sol_to_use) * 100
            

            THRESHOLD = 0

            if simulated_profit_pct < THRESHOLD:
                print(f"🔁 Step 2: 預估利潤 {simulated_profit_pct:.4f}% 低於 {THRESHOLD}% 門檻", end="\r", flush=True)
                continue


            print(f"🪙 預估利潤 {simulated_profit_pct:.4f}% 高於 {THRESHOLD}% 門檻")
            print(f"🔍 預期獲得 USDC: {int(q3['outAmount']) / 1e6:.6f} USDC")

            payload_3 = {"quoteResponse": q3, "userPublicKey": wallet_address, "wrapUnwrapSOL": True}
            swap_3 = requests.post(SWAP_API, json=payload_3).json()
            signed_tx_3 = VersionedTransaction.populate(
                VersionedTransaction.from_bytes(base64.b64decode(swap_3["swapTransaction"])).message,
                [keypair.sign_message(message.to_bytes_versioned(
                    VersionedTransaction.from_bytes(base64.b64decode(swap_3["swapTransaction"])).message))]
            )
            tx_id_3 = json.loads(client.send_raw_transaction(
                txn=bytes(signed_tx_3), opts=TxOpts(skip_preflight=False, preflight_commitment=Processed) #本來skip pre 是False
            ).to_json())["result"]

            print(f"✅ USDC → SOL 交易送出成功：https://solscan.io/tx/{tx_id_3}")
            confirm_state = confirm_tx(tx_id_3)


            # ✅ 這裡加入防呆：確認 SOL 有成功收到
            for i in range(2):  # 最多查 5 次，避免陷入死循環
                time.sleep(2)
                final_sol_balance_lamports = client.get_balance(wallet_pubkey).value
                final_sol_balance = final_sol_balance_lamports / LAMPORTS
                print(f"📊總共SOL 數量：{final_sol_balance:.6f} SOL")
                if final_sol_balance > 0.5: #至少有0.5錢
                    to_do = False
                    return 
                print("⚠️ 檢查到 SOL < 0.5，重新嘗試 Step 2...")


        except Exception as e:
            print(f"⚠️",end="")
            time.sleep(2)
        time.sleep(2)
    



# === 主套利流程 ===
def run_arbitrage():
    initial_sol_lamports = client.get_balance(wallet_pubkey).value
    sol_to_use = initial_sol_lamports * 0.9

    # 初始餘額
    initial_sol_lamports = client.get_balance(wallet_pubkey).value
    initial_sol_balance = initial_sol_lamports / LAMPORTS

    # 實際要用來套利的金額（90%）
    sol_to_use_lamports = int(initial_sol_lamports * 0.9)
    sol_to_use = sol_to_use_lamports / LAMPORTS
    print(f"🪙 初始 SOL 餘額：{initial_sol_balance:.6f} SOL（使用 90%：{sol_to_use:.6f} SOL）")

    # Step 1: SOL → USDC
    q1_outAmount = soltousdc(sol_to_use_lamports,sol_to_use)
    
    # check step 1 result
    usdc_balance = get_token_balance(USDC_MINT)
    print(f"📊 實際收到 USDc 數量：{usdc_balance:.6f} USDT")
    usdc_balance = int(usdc_balance * 1e6)

    step1_overearn = (usdc_balance - int(q1_outAmount))/int(q1_outAmount)*100
    print("這波多賺了：",step1_overearn ,"%")
    
    # Step 3: USDC → SOL
    usdctosol(usdc_balance,sol_to_use,step1_overearn)
    # check step 3 result
    final_sol_balance_lamports = client.get_balance(wallet_pubkey).value
    final_sol_balance = final_sol_balance_lamports / LAMPORTS
    reviced_sol = final_sol_balance - initial_sol_balance*0.1
    print(f"📊 實際收到 SOL 數量：{reviced_sol:.6f} USDT")
    print(f"\n📊 最後 SOL 餘額：{final_sol_balance:.6f} SOL")
    profit_ratio = ((final_sol_balance - initial_sol_balance) / initial_sol_balance) * 100
    print(f"📈 本次套利盈虧：{profit_ratio:.4f}%")
    time.sleep(5)


# === 執行主迴圈 ===
if __name__ == "__main__":
    import argparse
    import base64
    import json
    import time
    import requests
    import sys
    from solders.keypair import Keypair
    from solders.transaction import VersionedTransaction
    from solders import message
    from solders.signature import Signature
    from solders.pubkey import Pubkey
    from solana.rpc.api import Client
    from solana.rpc.types import TxOpts
    from solana.rpc.commitment import Processed, Finalized

    # === 設定 ===
    RPC_URL = "your_rpc_url"  # 替換為你的 RPC URL
    RPC_URL = "https://api.mainnet-beta.solana.com"
    QUOTE_API = "https://quote-api.jup.ag/v6/quote"
    SWAP_API = "https://quote-api.jup.ag/v6/swap"

    LAMPORTS = 1_000_000_000
    SLIPPAGE = 0.005  # 改為 0.5%，可依實際情況調整

    THRESHOLD_PROFIT_PERCENT = 0.01

    # === 代幣 Mint ===
    SOL_MINT = "So11111111111111111111111111111111111111112"
    USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
    USDT_MINT = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

    # === 初始化錢包與 RPC 連線 ===
    with open("keypair_old2.json", "r") as f:
        keypair = Keypair.from_json(json.load(f))

    wallet_pubkey = keypair.pubkey()
    wallet_address = str(wallet_pubkey)
    client = Client(RPC_URL)

    parser = argparse.ArgumentParser(description="Solana Arbitrage Bot")

    parser.add_argument("--restart", action="store_true", help="重新執行 USDC → SOL")
    parser.add_argument("--usdc_amount", type=int, help="USDC 數量（單位為最小單位，即1 USDC = 1000000）")
    parser.add_argument("--sol_to_use", type=float, help="SOL 使用量（單位為 SOL）")
    parser.add_argument("--step1_overearn", type=float, help="Step1 多賺的百分比，例如 0.01 表示多賺 1%")

    args = parser.parse_args()

    if args.restart:
        if args.usdc_amount is None or args.sol_to_use is None or args.step1_overearn is None:
            print("❌ 使用 --restart 時，必須提供 --usdc_amount, --sol_to_use, --step1_overearn")
            sys.exit(1)
        print("🔁 重新執行 USDC → SOL")
        # Step 3: USDC → SOL
        usdctosol(args.usdc_amount, args.sol_to_use, args.step1_overearn)
        # check step 3 result
        final_sol_balance_lamports = client.get_balance(wallet_pubkey).value
        final_sol_balance = final_sol_balance_lamports / LAMPORTS
        reviced_sol = final_sol_balance - (args.sol_to_use/0.9)*0.1
        print(f"📊 實際收到 SOL 數量：{reviced_sol:.6f} USDT")
        print(f"\n📊 最後 SOL 餘額：{final_sol_balance:.6f} SOL")
        profit_ratio = ((final_sol_balance - (args.sol_to_use/0.9)) / (args.sol_to_use/0.9)) * 100
        print(f"📈 本次套利盈虧：{profit_ratio:.4f}%")
        time.sleep(5)
        #python 95_64.py --restart --usdc_amount 213637894 --sol_to_use 1.723085 --step1_overearn 0.020671

    print("🔁 啟動套利模擬...")
    while True:
        run_arbitrage()
        time.sleep(2)