import time
from typing import Any, Dict

from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk import ed25519

from aptos_sdk.authenticator import (
    Authenticator,
    Ed25519Authenticator,
)

from aptos_sdk.bcs import Serializer

from aptos_sdk.transactions import (
    EntryFunction,
    RawTransaction,
    SignedTransaction,
    TransactionArgument,
    TransactionPayload,
)

from aptos_sdk.type_tag import StructTag, TypeTag

import cloudscraper
from datetime import datetime

import requests

NODE_URL = "https://aptos.m0n4.com/http/aptos/v1"

# change
PRIVATE_KEY = (
    "0x00...."  # HARDCODING IS BAD! PLEASE CHANGE IT TO THE ENVIRONMENT VARIABLE OR
)
MAX_GAS_AMOUNT = 330000  # 0.33 APT
TARGET_NFT_NAME = "bigfoot-town-public"
TARGET_NFT_MINT_TIME = "2022/10/22 01:00:00"

MINT_TIME_DURATION = 5

if __name__ == "__main__":

    private_key = ed25519.PrivateKey.from_hex(PRIVATE_KEY)
    account = Account(
        account_address=AccountAddress.from_key(private_key.public_key()),
        private_key=private_key,
    )

    rest_client = RestClient(NODE_URL)

    print("\n=== Addresses ===")
    print(f"Account: {account.address()}")

    # change
    element = datetime.strptime(TARGET_NFT_MINT_TIME, "%Y/%m/%d %H:%M:%S")
    tuple = element.timetuple()
    target_timestamp = round(time.mktime(tuple))

    while True:
        block_timestamp = int(
            requests.get(f"{NODE_URL}/transactions").json()[-1]["timestamp"][:-6]
        )
        mint_time = (target_timestamp - block_timestamp)
        if -MINT_TIME_DURATION < mint_time < MINT_TIME_DURATION:

            print("Collecting NFT data")

            scraper = cloudscraper.create_scraper(
                delay=10,
                browser={
                    "custom": "ScraperBot/1.0",
                },
            )
            # sometime bluemove leaks their contract address somehow, solve the puzzle yourself
            resp = scraper.get(
                f"https://aptos-mainnet-api.bluemove.net/api/launchpads?filters[launchpad_slug][$eq]={TARGET_NFT_NAME}&sort[0]=start_time%3Aasc"
            ).json()
            mint_target_address = resp["data"][0]["attributes"]["module_address"]
            print(f"Mint addr : {mint_target_address}")

            print("Minting NFT")

            # change
            transaction_arguments = [
                TransactionArgument(1, Serializer.u64),
            ]

            # change
            payload = EntryFunction.natural(
                f"{mint_target_address}::factory",
                "mint_with_quantity",
                [],
                transaction_arguments,
            )

            raw_transaction = RawTransaction(
                account.address(),
                rest_client.account_sequence_number(account.address()),
                TransactionPayload(payload),
                MAX_GAS_AMOUNT,
                100,
                int(time.time()) + 600,
                rest_client.chain_id,
            )

            signature = account.sign(raw_transaction.keyed())
            authenticator = Authenticator(
                Ed25519Authenticator(account.public_key(), signature)
            )
            signed_transaction = SignedTransaction(raw_transaction, authenticator)
            txn_hash = rest_client.submit_bcs_transaction(signed_transaction)
            rest_client.wait_for_transaction(txn_hash)
