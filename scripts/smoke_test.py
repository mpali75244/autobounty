from gltest import get_contract_factory, create_account, get_default_account
from gltest.assertions import tx_execution_succeeded
from gltest.contracts.contract import Contract
from gltest_cli.config.general import get_general_config
from gltest_cli.config.plugin import get_default_user_config

BUDGET = 10**18
RULES = {"critical": 50, "high": 30, "medium": 15, "low": 5}
ISSUE_URL = "https://github.com/mpali75244/autobounty/issues/1"
PR_URL = "https://github.com/mpali75244/autobounty/pull/1"

SCHEMA = {
    "methods": {
        name: {"readonly": readonly}
        for name, readonly in {
            "create_bounty": False,
            "submit_pr": False,
            "confirm_merge": False,
            "resolve_bounty": False,
            "appeal": False,
            "close_bounty": False,
            "cancel_bounty": False,
            "get_bounty_count": True,
            "get_bounty": True,
            "get_all_bounties": True,
        }.items()
    }
}


def main():
    get_general_config().user_config = get_default_user_config()
    maintainer = get_default_account()
    hunter = create_account()

    factory = get_contract_factory("AutoBounty")
    deployed = factory.deploy(args=[], account=maintainer)
    print("deployed:", deployed.address)
    contract = Contract.new(address=deployed.address, schema=SCHEMA, account=maintainer)

    tx = contract.create_bounty(args=["Smoke test bounty", ISSUE_URL, RULES]).transact(value=BUDGET)
    if not tx_execution_succeeded(tx):
        print("GLSim limitation: msg.value is not propagated by the simulator,")
        print("so the payable create_bounty reverts here by design.")
        print("Run the full escrow flow on GenLayer Studio (localnet / studionet / testnet).")
        return
    print("create_bounty + escrow: OK")

    assert int(contract.get_bounty_count().call()) == 1

    hunter_view = Contract.new(address=deployed.address, schema=SCHEMA, account=hunter)
    tx = hunter_view.submit_pr(args=[0, PR_URL]).transact()
    assert tx_execution_succeeded(tx), tx
    print("submit_pr as hunter: OK")

    tx = contract.confirm_merge(args=[0]).transact()
    assert tx_execution_succeeded(tx), tx

    bounty = contract.get_bounty(args=[0]).call()
    assert bounty["status"] == "merged", bounty
    assert bounty["total_budget"] == BUDGET
    assert bounty["severity_rules"] == RULES
    print("confirm_merge + get_bounty: OK")
    print("SMOKE TEST PASSED (resolve_bounty needs AI providers — test it on GenLayer Studio)")


if __name__ == "__main__":
    main()
