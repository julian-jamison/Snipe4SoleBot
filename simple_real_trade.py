import asyncio
import aiohttp
import base64
import requests
from decrypt_config import decrypt_config_file

async def execute_direct_jupiter_trade():
    print('🔴 Direct Jupiter trade execution...')
    
    # Get config - FIXED function name
    config = decrypt_config_file('config.enc')
    private_key_hex = config['wallet']['private_key']
    
    # Create keypair directly
    print('🔑 Creating keypair...')
    private_key_bytes = bytes.fromhex(private_key_hex)
    
    from solders.keypair import Keypair
    keypair = Keypair.from_bytes(private_key_bytes)
    wallet_pubkey = str(keypair.pubkey())
    
    print(f'Wallet: {wallet_pubkey}')
    
    # Check balance with working RPC
    working_rpc = 'https://api.mainnet-beta.solana.com'
    
    print('💰 Checking balance...')
    balance_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getBalance',
        'params': [wallet_pubkey]
    }
    
    balance_response = requests.post(working_rpc, json=balance_payload)
    if not balance_response.ok:
        print(f'❌ Balance check failed: {balance_response.text}')
        return False
    
    balance_data = balance_response.json()
    lamports = balance_data['result']['value']
    sol_balance = lamports / 1e9
    
    print(f'💰 Balance: {sol_balance:.6f} SOL')
    
    if sol_balance < 0.005:
        print('❌ Insufficient balance for trade')
        return False
    
    # Get Jupiter quote
    print('📊 Getting Jupiter quote...')
    
    quote_url = 'https://quote-api.jup.ag/v6/quote'
    quote_params = {
        'inputMint': 'So11111111111111111111111111111111111111112',  # SOL
        'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
        'amount': str(int(0.001 * 1e9)),  # 0.001 SOL in lamports
        'slippageBps': '100'  # 1%
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(quote_url, params=quote_params) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f'❌ Quote error {response.status}: {error_text}')
                return False
            
            quote = await response.json()
            in_amount = int(quote['inAmount'])
            out_amount = int(quote['outAmount'])
            
            print(f'✅ Quote: {in_amount / 1e9:.6f} SOL → {out_amount / 1e6:.6f} USDC')
    
    # Get swap transaction
    print('🔄 Getting swap transaction...')
    
    swap_url = 'https://quote-api.jup.ag/v6/swap'
    swap_payload = {
        'quoteResponse': quote,
        'userPublicKey': wallet_pubkey,
        'wrapAndUnwrapSol': True,
        'dynamicComputeUnitLimit': True,
        'prioritizationFeeLamports': 'auto'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(swap_url, json=swap_payload) as response:
            if response.status != 200:
                error_text = await response.text()
                print(f'❌ Swap error {response.status}: {error_text}')
                return False
            
            swap_data = await response.json()
            
            if 'swapTransaction' not in swap_data:
                print(f'❌ No swap transaction: {swap_data}')
                return False
            
            swap_transaction_b64 = swap_data['swapTransaction']
            print('✅ Got swap transaction from Jupiter')
    
    # Sign and send transaction
    print('🔐 Signing transaction...')
    
    # Decode transaction
    tx_bytes = base64.b64decode(swap_transaction_b64)
    
    # Import required classes
    from solders.transaction import VersionedTransaction
    
    # Deserialize transaction
    transaction = VersionedTransaction.from_bytes(tx_bytes)
    print('✅ Transaction deserialized')
    
    # Sign the message
    message_bytes = bytes(transaction.message)
    signature = keypair.sign_message(message_bytes)
    print('✅ Transaction signed')
    
    # Create new signed transaction
    signed_tx = VersionedTransaction([signature], transaction.message)
    
    # Serialize for sending
    signed_tx_bytes = bytes(signed_tx)
    signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8')
    
    # Send via RPC
    print('📡 Broadcasting to Solana network...')
    
    rpc_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'sendTransaction',
        'params': [
            signed_tx_b64,
            {
                'encoding': 'base64',
                'maxRetries': 3,
                'skipPreflight': False
            }
        ]
    }
    
    rpc_response = requests.post(working_rpc, json=rpc_payload, timeout=30)
    
    if rpc_response.ok:
        rpc_data = rpc_response.json()
        
        if 'result' in rpc_data:
            tx_signature = rpc_data['result']
            print('')
            print('🎉 TRANSACTION SUCCESSFUL!')
            print(f'🔗 Signature: {tx_signature}')
            print(f'🔍 Solscan: https://solscan.io/tx/{tx_signature}')
            print('')
            return True
            
        elif 'error' in rpc_data:
            error_info = rpc_data['error']
            print(f'❌ Transaction failed: {error_info}')
            return False
        else:
            print(f'❌ Unexpected response: {rpc_data}')
            return False
    else:
        print(f'❌ RPC failed: {rpc_response.status_code}')
        print(f'Response: {rpc_response.text}')
        return False

# Execute the trade
print('🚀 Direct Jupiter Real Trading Test')
print('=' * 60)

confirm = input('Execute REAL \$0.17 trade? (yes/no): ')
if confirm.lower() == 'yes':
    success = asyncio.run(execute_direct_jupiter_trade())
    if success:
        print()
        print('='*60)
        print('🎉 SUCCESS! Your first real Jupiter trade executed!')
        print('Your Solana trading bot is now LIVE and functional!')
        print('='*60)
    else:
        print('❌ Direct trade failed')
else:
    print('Test cancelled')

