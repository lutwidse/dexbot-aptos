import time
from typing import Any, Dict

from aptos_sdk.account import Account
from aptos_sdk.account_address import AccountAddress
from aptos_sdk.client import RestClient
from aptos_sdk import ed25519

NODE_URL = "https://rpc.ankr.com/http/aptos/v1"
CONTRACT = "0x00...."


class BotClient(RestClient):
    def submit_transaction(self, sender: Account, payload: Dict[str, Any]) -> str:
        """Potentially initialize and set the resource message::MessageHolder::message"""

        txn_request = {
            "sender": f"{sender.address()}",
            "sequence_number": str(self.account_sequence_number(sender.address())),
            "max_gas_amount": "10000",
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


if __name__ == "__main__":

    private_key = ed25519.PrivateKey.from_hex("paste_your_private_key_here")
    account = Account(
    account_address=AccountAddress.from_key(private_key.public_key()),
    private_key=private_key,
)

    rest_client = BotClient(NODE_URL)

    print("\n=== Addresses ===")
    print(f"Account: {account.address()}")

    print("Minting NFT")
    payload = {
        "function": f"{CONTRACT}::factory::mint_nft",
        "type_arguments": [],
        "arguments": [],
        "type": "entry_function_payload",
    }
    txn_hash = rest_client.submit_transaction(account, payload)
    rest_client.wait_for_transaction(txn_hash)
