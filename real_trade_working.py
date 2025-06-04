import asyncio
import aiohttp
import base64
import requests

async def execute_direct_jupiter_trade():
    print('🔴 Direct Jupiter trade execution...')
    
    # Use the direct config import that works
    from decrypt_config import config
    
    # Get private key from correct location
    wallets = config['solana_wallets']
    
    # The private key is directly in private_key_hex
    if 'private_key_hex' in wallets:
        private_key_hex = wallets['private_key_hex']
        print('✅ Found private_key_hex in config')
    else:
        print('❌ No private_key_hex found')
        return False
    
    print('🔑 Creating keypair...')
    private_key_bytes = bytes.fromhex(private_key_hex)
    
    from solders.keypair import Keypair
    keypair = Keypair.from_bytes(private_key_bytes)
    wallet_pubkey = str(keypair.pubkey())
    
    print(f'Wallet: {wallet_pubkey}')
    
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
    
    print('📊 Getting Jupiter quote...')
    
    quote_url = 'https://quote-api.jup.ag/v6/quote'
    quote_params = {
        'inputMint': 'So11111111111111111111111111111111111111112',
        'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'amount': str(int(0.001 * 1e9)),
        'slippageBps': '100'
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
    
    print('🔐 Signing transaction...')
    
    try:
        tx_bytes = base64.b64decode(swap_transaction_b64)
        
        from solders.transaction import VersionedTransaction
        
        transaction = VersionedTransaction.from_bytes(tx_bytes)
        print('✅ Transaction deserialized')
        
        message_bytes = bytes(transaction.message)
        signature = keypair.sign_message(message_bytes)
        print('✅ Transaction signed')
        
        signed_tx = VersionedTransaction([signature], transaction.message)
        
        signed_tx_bytes = bytes(signed_tx)
        signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8')
        
        print('📡 Broadcasting to Solana network...')
        print('🔥 THIS IS A REAL TRANSACTION ON MAINNET! 🔥')
        
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
                print('🎉🎉🎉 TRANSACTION SUCCESSFUL! 🎉🎉🎉')
                print(f'🔗 Signature: {tx_signature}')
                print(f'🔍 Solscan: https://solscan.io/tx/{tx_signature}')
                print(f'🌍 Explorer: https://explorer.solana.com/tx/{tx_signature}')
                print('')
                
                print('⏳ Waiting 10 seconds for confirmation...')
                await asyncio.sleep(10)
                
                final_balance_response = requests.post(working_rpc, json=balance_payload)
                if final_balance_response.ok:
                    final_balance_data = final_balance_response.json()
                    final_lamports = final_balance_data['result']['value']
                    final_sol_balance = final_lamports / 1e9
                    
                    spent = sol_balance - final_sol_balance
                    print(f'💰 Final balance: {final_sol_balance:.6f} SOL')
                    print(f'💸 SOL spent: {spent:.6f} SOL (${spent * 174:.2f})')
                
                return True
                
            elif 'error' in rpc_data:
                error_info = rpc_data['error']
                print(f'❌ Transaction failed: {error_info}')
                
                # Parse common errors
                error_str = str(error_info).lower()
                if 'insufficient funds' in error_str:
                    print('💡 Solution: Add more SOL to your wallet')
                elif 'blockhash' in error_str:
                    print('💡 Solution: Try again (network congestion)')
                elif 'slippage' in error_str:
                    print('💡 Solution: Increase slippage tolerance')
                
                return False
            else:
                print(f'❌ Unexpected response: {rpc_data}')
                return False
        else:
            print(f'❌ RPC failed: {rpc_response.status_code}')
            print(f'Response: {rpc_response.text}')
            return False
            
    except Exception as e:
        print(f'❌ Transaction error: {str(e)}')
        import traceback
        print(f'Traceback: {traceback.format_exc()}')
        return False

def main():
    print('🚀 WORKING Jupiter Real Trading Test')
    print('=' * 60)
    print('This will execute a REAL trade on Solana mainnet!')
    print('Amount: 0.001 SOL (~$0.17) → USDC')
    print('=' * 60)
    
    confirm = input('🔥 EXECUTE REAL TRADE? (yes/no): ')
    if confirm.lower() == 'yes':
        success = asyncio.run(execute_direct_jupiter_trade())
        if success:
            print()
            print('='*60)
            print('🎉 HISTORIC MOMENT! Your first real trade executed!')
            print('🤖 Your Solana trading bot is now LIVE!')
            print('💰 You just swapped SOL for USDC on Jupiter!')
            print('='*60)
        else:
            print()
            print('❌ Trade failed - but we are so close!')
    else:
        print('Trade cancelled')

if __name__ == "__main__":
    main()
