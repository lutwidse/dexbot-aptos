import time
from typing import Any, Dict

from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk import ed25519

import cloudscraper
from datetime import datetime

NODE_URL = "https://rpc.ankr.com/http/aptos/v1"


class BotClient(RestClient):
    def submit_transaction(self, sender: Account, payload: Dict[str, Any]) -> str:
        txn_request = {
            "sender": f"{sender.address()}",
            "sequence_number": str(self.account_sequence_number(sender.address())),
            "max_gas_amount": "1000",
            "gas_unit_price": "100",
            "expiration_timestamp_secs": str(int(time.time()) + 600),
            "payload": payload,
        }
        response = self.client.post(
            f"{NODE_URL}/transactions/encode_submission", json=txn_request
        )
        if response.status_code >= 400:
            print(f"{response.text}, {response.status_code}")

        to_sign = bytes.fromhex(response.json()[2:])
        signature = sender.sign(to_sign)
        txn_request["signature"] = {
            "type": "ed25519_signature",
            "public_key": f"{sender.public_key()}",
            "signature": f"{signature}",
        }

        headers = {"Content-Type": "application/json"}
        response = self.client.post(
            f"{NODE_URL}/transactions", headers=headers, json=txn_request
        )
        if response.status_code >= 400:
            print(f"{response.text}, {response.status_code}")
        return response.json()["hash"]
        # we have to fix the error {"message":"Invalid transaction: Type: InvariantViolation Code: VM_STARTUP_FAILURE","error_code":"vm_error","vm_error_code":2012}


if __name__ == "__main__":

    private_key = ed25519.PrivateKey.from_hex("0x00")
    account = Account(
        account_address=AccountAddress.from_key(private_key.public_key()),
        private_key=private_key,
    )

    rest_client = BotClient(NODE_URL)

    print("\n=== Addresses ===")
    print(f"Account: {account.address()}")

    # change
    mint_time = "2022/10/22 01:00:00"
    element = datetime.strptime(mint_time, "%Y/%m/%d %H:%M:%S")
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
            target_nft_name = "bigfoot-town-public"
            # sometime bluemove leaks their contract address somehow
            resp = scraper.get(
                f"https://aptos-mainnet-api.bluemove.net/api/launchpads?filters[collection_slug][$eq]={target_nft_name}&sort[0]=start_time%3Aasc"
            ).json()
            mint_target_address = resp["data"][0]["attributes"]["module_address"]
            print(f"Mint addr : {mint_target_address}")

            print("Minting NFT")
            payload = {
                "type": "entry_function_payload",
                # change
                "function": f"mint_target_address::factory::mint_with_quantity",
                "type_arguments": [],
                "arguments": ["2"],
            }
            txn_hash = rest_client.submit_transaction(account, payload)
            rest_client.wait_for_transaction(txn_hash)
