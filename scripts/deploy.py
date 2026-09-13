from gltest import get_contract_factory
from gltest_cli.config.general import get_general_config
from gltest_cli.config.plugin import get_default_user_config


def main():
    get_general_config().user_config = get_default_user_config()
    factory = get_contract_factory("AutoBounty")
    contract = factory.deploy(args=[])
    print("AutoBounty deployed at:", contract.address)


if __name__ == "__main__":
    main()
