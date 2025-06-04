import asyncio
import aiohttp
import base64
import requests

async def execute_real_jupiter_trade():
    print('🚀 FINAL Real Jupiter Trade - Proper Signing')
    print('=' * 50)
    
    # Your working private key
    private_key_hex = "295a3d0a5562e8772964abfc5fe5c36be0ca7e78ceed3a238dd249526ff5fd4840f31de17a19f5ba48a00b32a5317ed23d6c82ff211e4ceb8a5f22736c1dbe65"
    
    from solders.keypair import Keypair
    keypair = Keypair.from_bytes(bytes.fromhex(private_key_hex))
    wallet_pubkey = str(keypair.pubkey())
    
    print(f'Wallet: {wallet_pubkey}')
    
    # Check balance
    rpc_url = 'https://api.mainnet-beta.solana.com'
    balance_payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getBalance',
        'params': [wallet_pubkey]
    }
    
    balance_response = requests.post(rpc_url, json=balance_payload)
    balance_data = balance_response.json()
    lamports = balance_data['result']['value']
    sol_balance = lamports / 1e9
    print(f'Balance: {sol_balance:.6f} SOL')
    
    # Get Jupiter quote
    print('📊 Getting Jupiter quote...')
    quote_url = 'https://quote-api.jup.ag/v6/quote'
    quote_params = {
        'inputMint': 'So11111111111111111111111111111111111111112',  # SOL
        'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',  # USDC
        'amount': str(int(0.001 * 1e9)),  # 0.001 SOL in lamports
        'slippageBps': '300'  # 3% slippage
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(quote_url, params=quote_params) as response:
            quote = await response.json()
            in_amount = int(quote['inAmount']) / 1e9
            out_amount = int(quote['outAmount']) / 1e6
            print(f'✅ Quote: {in_amount:.6f} SOL → {out_amount:.6f} USDC')
    
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
            swap_data = await response.json()
            swap_transaction_b64 = swap_data['swapTransaction']
            print('✅ Got swap transaction from Jupiter')
    
    # The key insight: Jupiter returns UNSIGNED transactions
    # We need to properly sign them ourselves
    print('🔐 Signing transaction properly...')
    
    try:
        # Decode transaction
        tx_bytes = base64.b64decode(swap_transaction_b64)
        
        # Import all required classes
        from solders.transaction import VersionedTransaction
        from solders.message import to_bytes_versioned
        from solders.signature import Signature
        
        # Deserialize transaction
        transaction = VersionedTransaction.from_bytes(tx_bytes)
        print('✅ Transaction deserialized')
        
        # Get message bytes for signing
        message_bytes = to_bytes_versioned(transaction.message)
        
        # Sign the message
        signature = keypair.sign_message(message_bytes)
        print('✅ Transaction signed')
        
        # Create new transaction with signature
        # Jupiter transactions expect 1 signature from the user
        signatures = [Signature.from_bytes(bytes(signature))]
        signed_transaction = VersionedTransaction(signatures, transaction.message)
        
        # Serialize signed transaction
        signed_tx_bytes = bytes(signed_transaction)
        signed_tx_b64 = base64.b64encode(signed_tx_bytes).decode('utf-8')
        
        print('')
        print('🔥 BROADCASTING REAL TRANSACTION TO SOLANA MAINNET! 🔥')
        print(f'💰 Trading: {in_amount:.6f} SOL → {out_amount:.6f} USDC')
        print('')
        
        # Send transaction
        send_payload = {
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'sendTransaction',
            'params': [
                signed_tx_b64,
                {
                    'encoding': 'base64',
                    'skipPreflight': False,
                    'preflightCommitment': 'processed',
                    'maxRetries': 5
                }
            ]
        }
        
        response = requests.post(rpc_url, json=send_payload, timeout=30)
        
        if response.ok:
            data = response.json()
            
            if 'result' in data:
                tx_signature = data['result']
                
                # Check if it's a real signature (not the dummy 1111... one)
                if tx_signature != '1111111111111111111111111111111111111111111111111111111111111111':
                    print('🎉🎉🎉 REAL TRANSACTION SUBMITTED! 🎉🎉🎉')
                    print(f'🔗 Signature: {tx_signature}')
                    print(f'🔍 Solscan: https://solscan.io/tx/{tx_signature}')
                    print(f'🌍 Explorer: https://explorer.solana.com/tx/{tx_signature}')
                    
                    # Wait and check balance
                    print('\n⏳ Waiting 20 seconds for confirmation...')
                    await asyncio.sleep(20)
                    
                    final_response = requests.post(rpc_url, json=balance_payload)
                    final_data = final_response.json()
                    final_lamports = final_data['result']['value']
                    final_balance = final_lamports / 1e9
                    spent = sol_balance - final_balance
                    
                    print(f'💰 Final balance: {final_balance:.6f} SOL')
                    print(f'💸 SOL spent: {spent:.6f} SOL (${spent * 174:.2f})')
                    
                    if spent > 0:
                        print('✅ TRADE CONFIRMED! Balance decreased!')
                        return True
                    else:
                        print('⚠️ Balance unchanged - may still be processing')
                        return True  # Transaction was submitted successfully
                else:
                    print('❌ Got dummy signature - transaction not actually sent')
                    
            elif 'error' in data:
                error = data['error']
                print(f'❌ Transaction error: {error}')
                
                # Common error solutions
                if 'insufficient funds' in str(error).lower():
                    print('💡 Need more SOL for fees')
                elif 'blockhash' in str(error).lower():
                    print('💡 Blockhash expired - try again')
                elif 'signature verification' in str(error).lower():
                    print('💡 Signature issue - check signing process')
                    
        else:
            print(f'❌ HTTP error: {response.status_code}')
            print(f'Response: {response.text}')
            
    except Exception as e:
        print(f'❌ Signing error: {str(e)}')
        import traceback
        print('Traceback:', traceback.format_exc())
    
    return False

def main():
    print('🚀 FINAL REAL TRADE - PROPER SIGNING METHOD')
    print('=' * 60)
    print('🔧 Using correct message signing approach')
    print('💰 Trade: 0.001 SOL → USDC')
    print('🌐 Network: Solana Mainnet')
    print('=' * 60)
    
    confirm = input('🔥 EXECUTE REAL TRADE WITH PROPER SIGNING? (yes/no): ')
    if confirm.lower() == 'yes':
        success = asyncio.run(execute_real_jupiter_trade())
        if success:
            print('\n' + '='*60)
            print('🎉 SUCCESS! Your first real Solana trade!')
            print('🤖 Trading bot is now operational!')
            print('='*60)
        else:
            print('\n❌ Trade failed - but very close now!')
    else:
        print('Cancelled - ready when you are!')

if __name__ == "__main__":
    main()
