import requests
import json

def check_transaction_status():
    print('🔍 Checking your transaction status...')
    
    tx_signature = "2ud7ixEqVGd1G8qbgfkVYebjDVejBPkCzrWBKeqrCFnxU6NQPW7rdScebe4VKmtMbDX3xW74d9Fk8xvTUcyKEHBV"
    rpc_url = 'https://api.mainnet-beta.solana.com'
    
    # Get transaction details
    payload = {
        'jsonrpc': '2.0',
        'id': 1,
        'method': 'getTransaction',
        'params': [
            tx_signature,
            {
                'encoding': 'jsonParsed',
                'commitment': 'confirmed',
                'maxSupportedTransactionVersion': 0
            }
        ]
    }
    
    response = requests.post(rpc_url, json=payload)
    
    if response.ok:
        data = response.json()
        
        if data.get('result') is None:
            print('❌ Transaction not found or not confirmed yet')
            print('💡 This could mean:')
            print('   - Transaction is still being processed')
            print('   - Transaction failed and was dropped')
            print('   - Transaction expired due to old blockhash')
            
            # Check if transaction signature exists in mempool
            signature_payload = {
                'jsonrpc': '2.0',
                'id': 1,
                'method': 'getSignatureStatuses',
                'params': [[tx_signature]]
            }
            
            sig_response = requests.post(rpc_url, json=signature_payload)
            if sig_response.ok:
                sig_data = sig_response.json()
                print(f'📊 Signature status: {sig_data}')
            
            return False
        else:
            result = data['result']
            print('✅ Transaction found!')
            print(f'🔗 Signature: {tx_signature}')
            print(f'📊 Slot: {result.get("slot", "Unknown")}')
            print(f'💰 Fee: {result["meta"]["fee"] / 1e9:.9f} SOL')
            
            # Check if transaction succeeded
            if result['meta']['err'] is None:
                print('✅ Transaction SUCCEEDED!')
                
                # Look for token changes
                if 'postTokenBalances' in result['meta'] or 'preTokenBalances' in result['meta']:
                    print('💱 Token balance changes detected!')
                    
                    pre_balances = result['meta'].get('preTokenBalances', [])
                    post_balances = result['meta'].get('postTokenBalances', [])
                    
                    print('📈 Token Balance Changes:')
                    for balance in post_balances:
                        if balance.get('mint') == 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v':  # USDC
                            amount = float(balance['uiTokenAmount']['uiAmount'] or 0)
                            print(f'   💰 USDC: +{amount:.6f}')
                
                # Check SOL balance changes
                pre_sol = result['meta']['preBalances'][0] / 1e9
                post_sol = result['meta']['postBalances'][0] / 1e9
                sol_change = post_sol - pre_sol
                
                print(f'💸 SOL Balance Change: {sol_change:.9f} SOL')
                
                if sol_change < 0:
                    print('✅ SOL was spent - trade likely executed!')
                else:
                    print('❓ No SOL spent - checking what happened...')
                
                return True
            else:
                print(f'❌ Transaction FAILED: {result["meta"]["err"]}')
                return False
    else:
        print(f'❌ RPC Error: {response.status_code}')
        print(f'Response: {response.text}')
        return False

if __name__ == "__main__":
    check_transaction_status()
