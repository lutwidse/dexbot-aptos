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

NODE_URL = "https://rpc.ankr.com/http/aptos/v1"

# change
MAX_GAS_AMOUNT = 3000
TARGET_NFT_NAME = "bigfoot-town-public"
TARGET_NFT_MINT_TIME = "2022/10/22 01:00:00"

class BotClient(RestClient):
    def submit_bcs_transaction(self, signed_transaction: SignedTransaction) -> str:
        headers = {"Content-Type": "application/x.aptos.signed_transaction+bcs"}
        response = self.client.post(
            f"{self.base_url}/transactions",
            headers=headers,
            content=signed_transaction.bytes(),
        )
        if response.status_code >= 400:
            print(f"{response.text} {response.status_code}")
        return response.json()["hash"]


if __name__ == "__main__":

    private_key = ed25519.PrivateKey.from_hex("0x00....")
    account = Account(
        account_address=AccountAddress.from_key(private_key.public_key()),
        private_key=private_key,
    )

    rest_client = BotClient(NODE_URL)

    print("\n=== Addresses ===")
    print(f"Account: {account.address()}")

    # change
    element = datetime.strptime(TARGET_NFT_MINT_TIME, "%Y/%m/%d %H:%M:%S")
    tuple = element.timetuple()
    target_timestamp = round(time.mktime(tuple))
    now_timestamp = round(datetime.timestamp(datetime.now()))

    while True:
        if (target_timestamp - now_timestamp) < 0:
            print("Collecting NFT data")
            scraper = cloudscraper.create_scraper(
                delay=10,
                browser={
                    "custom": "ScraperBot/1.0",
                },
            )
            # sometime bluemove leaks their contract address somehow
            resp = scraper.get(
                f"https://aptos-mainnet-api.bluemove.net/api/launchpads?filters[launchpad_slug][$eq]={TARGET_NFT_NAME}&sort[0]=start_time%3Aasc"
            ).json()
            mint_target_address = resp["data"][0]["attributes"]["module_address"]
            print(f"Mint addr : {mint_target_address}")

            print("Minting NFT")

            # change
            transaction_arguments = [
                TransactionArgument(2, Serializer.u64),
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
