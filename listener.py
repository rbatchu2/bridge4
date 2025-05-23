from web3 import Web3
from web3.providers.rpc import HTTPProvider
from web3.middleware import ExtraDataToPOAMiddleware
from pathlib import Path
import json
from datetime import datetime
import pandas as pd

def scan_blocks(chain, start_block, end_block, contract_address, eventfile='deposit_logs.csv'):
    if chain == 'avax':
        api_url = f"https://api.avax-test.network/ext/bc/C/rpc"

    if chain == 'bsc':
        api_url = f"https://data-seed-prebsc-1-s1.binance.org:8545/"

    if chain in ['avax', 'bsc']:
        w3 = Web3(Web3.HTTPProvider(api_url))
        w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    else:
        w3 = Web3(Web3.HTTPProvider(api_url))

    DEPOSIT_ABI = json.loads('[ { "anonymous": false, "inputs": [ { "indexed": true, "internalType": "address", "name": "token", "type": "address" }, { "indexed": true, "internalType": "address", "name": "recipient", "type": "address" }, { "indexed": false, "internalType": "uint256", "name": "amount", "type": "uint256" } ], "name": "Deposit", "type": "event" }]')
    contract = w3.eth.contract(address=contract_address, abi=DEPOSIT_ABI)

    arg_filter = {}

    if start_block == "latest":
        start_block = w3.eth.get_block_number()
    if end_block == "latest":
        end_block = w3.eth.get_block_number()

    if end_block < start_block:
        print(f"Error end_block < start_block!")
        print(f"end_block = {end_block}")
        print(f"start_block = {start_block}")
        return

    if start_block == end_block:
        print(f"Scanning block {start_block} on {chain}")
    else:
        print(f"Scanning blocks {start_block} - {end_block} on {chain}")

    event_list = []

    def process_events(events):
        for event in events:
            block_number = event.blockNumber
            token = event.args.token
            recipient = event.args.recipient
            amount = event.args.amount
            timestamp = w3.eth.get_block(block_number)['timestamp']
            transaction_hash = event.transactionHash.hex()
            event_list.append({
                "block_number": block_number,
                "token": token,
                "recipient": recipient,
                "amount": amount,
                "timestamp": datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                "transactionHash": transaction_hash
            })

    if end_block - start_block < 30:
        event_filter = contract.events.Deposit.create_filter(from_block=start_block, to_block=end_block, argument_filters=arg_filter)
        events = event_filter.get_all_entries()
        process_events(events)
    else:
        for block_num in range(start_block, end_block + 1):
            event_filter = contract.events.Deposit.create_filter(from_block=block_num, to_block=block_num, argument_filters=arg_filter)
            events = event_filter.get_all_entries()
            process_events(events)

    if event_list:
        df = pd.DataFrame(event_list)
        if Path(eventfile).is_file():
            df.to_csv(eventfile, mode='a', header=False, index=False)
        else:
            df.to_csv(eventfile, mode='w', header=True, index=False)
        print(f"Successfully saved {len(event_list)} events to {eventfile}")
    else:
        print("No events found.")
