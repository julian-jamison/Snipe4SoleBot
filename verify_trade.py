import asyncio
import aiohttp
import base64
import requests

async def test_jupiter_transaction():
    print('🔍 Testing Jupiter transaction creation...')
    
    private_key_hex = "295a3d0a5562e8772964abfc5fe5c36be0ca7e78ceed3a238dd249526ff5fd4840f31de17a19f5ba48a00b32a5317ed23d6c82ff211e4ceb8a5f22736c1dbe65"
    
    from solders.keypair import Keypair
    keypair = Keypair.from_bytes(bytes.fromhex(private_key_hex))
    wallet_pubkey = str(keypair.pubkey())
    
    print(f'Wallet: {wallet_pubkey}')
    
    # Get Jupiter quote
    quote_url = 'https://quote-api.jup.ag/v6/quote'
    quote_params = {
        'inputMint': 'So11111111111111111111111111111111111111112',
        'outputMint': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'amount': str(int(0.001 * 1e9)),
        'slippageBps': '100'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(quote_url, params=quote_params) as response:
            quote = await response.json()
            print(f'Quote received: {quote["inAmount"]} → {quote["outAmount"]}')
    
    # Get swap transaction
    swap_url = 'https://quote-api.jup.ag/v6/swap'
    swap_payload = {
        'quoteResponse': quote,
        'userPublicKey': wallet_pubkey,
        'wrapAndUnwrapSol': True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(swap_url, json=swap_payload) as response:
            swap_data = await response.json()
            
            if 'swapTransaction' not in swap_data:
                print(f'❌ No swap transaction returned')
                print(f'Response: {swap_data}')
                return
            
            swap_transaction_b64 = swap_data['swapTransaction']
            print('✅ Got Jupiter transaction')
            
            # Decode and examine transaction
            tx_bytes = base64.b64decode(swap_transaction_b64)
            print(f'Transaction size: {len(tx_bytes)} bytes')
            
            # Check if it's a valid transaction by trying to deserialize
            from solders.transaction import VersionedTransaction
            try:
                transaction = VersionedTransaction.from_bytes(tx_bytes)
                print('✅ Transaction is valid and deserializable')
                print(f'Signatures needed: {len(transaction.message.header.num_required_signatures)}')
                
                # Try direct submission without additional signing
                print('🧪 Testing direct submission...')
                
                rpc_payload = {
                    'jsonrpc': '2.0',
                    'id': 1,
                    'method': 'sendTransaction',
                    'params': [
                        swap_transaction_b64,
                        {
                            'encoding': 'base64',
                            'skipPreflight': True
                        }
                    ]
                }
                
                rpc_response = requests.post('https://api.mainnet-beta.solana.com', 
                                           json=rpc_payload, timeout=15)
                
                if rpc_response.ok:
                    rpc_data = rpc_response.json()
                    print(f'RPC Response: {rpc_data}')
                    
                    if 'result' in rpc_data and rpc_data['result'] != '1111111111111111111111111111111111111111111111111111111111111111':
                        print(f'✅ REAL TRANSACTION SUBMITTED: {rpc_data["result"]}')
                        print(f'🔍 Check: https://solscan.io/tx/{rpc_data["result"]}')
                        return True
                    else:
                        print('❌ Got placeholder response or error')
                else:
                    print(f'❌ RPC failed: {rpc_response.status_code}')
                    print(f'Response: {rpc_response.text}')
                
            except Exception as e:
                print(f'❌ Transaction deserialization failed: {e}')
    
    return False

if __name__ == "__main__":
    asyncio.run(test_jupiter_transaction())
