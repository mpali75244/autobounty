import json
from pathlib import Path

CONTRACT = str(Path(__file__).resolve().parent.parent / "contracts" / "autobounty.py")

RULES = {"critical": 50, "high": 30, "medium": 15, "low": 5}
BUDGET = 10**18

ISSUE_URL = "https://github.com/acme/app/issues/1"
PR_URL = "https://github.com/acme/app/pull/2"

ISSUE_JSON = json.dumps(
    {"title": "Crash on negative deposit", "body": "Entering a negative deposit crashes the whole app"}
)
PR_JSON = json.dumps({"title": "Fix negative deposit crash", "body": "Adds input validation"})
DIFF = (
    "diff --git a/app.py b/app.py\n"
    "--- a/app.py\n"
    "+++ b/app.py\n"
    "@@ -1 +1 @@\n"
    "-amount = int(x)\n"
    "+amount = max(0, int(x))"
)

HIGH_DECISION = json.dumps({"severity": "high", "reasoning": "major feature broken", "confidence": 85})
HIGH_ALT_WORDS = json.dumps({"severity": "high", "reasoning": "input handling defect with user impact", "confidence": 71})
CRITICAL_DECISION = json.dumps({"severity": "critical", "reasoning": "funds at risk", "confidence": 90})
LOW_DECISION = json.dumps({"severity": "low", "reasoning": "cosmetic", "confidence": 60})


def setup_web_mocks(vm):
    vm.mock_web(r"api\.github\.com/repos/acme/app/issues/1", {"status": 200, "body": ISSUE_JSON})
    vm.mock_web(r"api\.github\.com/repos/acme/app/pulls/2", {"status": 200, "body": PR_JSON})
    vm.mock_web(r"github\.com/acme/app/pull/2\.diff", {"status": 200, "body": DIFF})


def deploy_with_bounty(direct_vm, direct_deploy, maintainer):
    setup_web_mocks(direct_vm)
    direct_vm.mock_llm(r"security judge", HIGH_DECISION)
    direct_vm.mock_llm(r"exactly the same value", "true")
    direct_vm.sender = maintainer
    direct_vm.value = BUDGET
    contract = direct_deploy(CONTRACT)
    contract.create_bounty("Fix negative deposit crash", ISSUE_URL, RULES)
    direct_vm.value = 0
    return contract


def test_create_bounty_rejects_invalid_input(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    direct_vm.value = BUDGET
    contract = direct_deploy(CONTRACT)
    with direct_vm.expect_revert("percentages must sum to 100"):
        contract.create_bounty("Fix crash", ISSUE_URL, {"critical": 50, "high": 25, "medium": 15, "low": 5})
    with direct_vm.expect_revert("misses 'low'"):
        contract.create_bounty("Fix crash", ISSUE_URL, {"critical": 50, "high": 30, "medium": 20})
    with direct_vm.expect_revert("must be 1..99"):
        contract.create_bounty("Fix crash", ISSUE_URL, {"critical": 100, "high": 0, "medium": 0, "low": 0})
    with direct_vm.expect_revert("github issue url"):
        contract.create_bounty("Fix crash", "https://example.com/not-github", RULES)
    with direct_vm.expect_revert("title must not be empty"):
        contract.create_bounty("   ", ISSUE_URL, RULES)
    direct_vm.value = 0
    with direct_vm.expect_revert("send GEN"):
        contract.create_bounty("Fix crash", ISSUE_URL, RULES)


def test_submit_pr_guards(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("github pull request url"):
        contract.submit_pr(0, "https://example.com/pr/2")
    with direct_vm.expect_revert("maintainer cannot submit"):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("not open for submissions"):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice), direct_vm.expect_revert("bounty not found"):
        contract.confirm_merge(7)
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("only the maintainer"):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_alice), direct_vm.expect_revert("no PR is submitted yet"):
        contract.confirm_merge(0)


def test_resolve_pays_hunter_by_consensus(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_bob):
        contract.resolve_bounty(0)
    b = contract.get_bounty(0)
    assert b["status"] == "resolved"
    assert b["resolved_severity"] == "high"
    assert b["payout_amount"] == BUDGET * 30 // 100
    assert b["reasoning"] == "major feature broken"
    assert b["total_transferred"] == BUDGET * 30 // 100
    assert contract.get_bounty_count() == 1


def test_validator_accepts_same_severity_with_different_words(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_bob):
        contract.resolve_bounty(0)
    direct_vm.clear_mocks()
    setup_web_mocks(direct_vm)
    direct_vm.mock_llm(r"security judge", HIGH_ALT_WORDS)
    direct_vm.mock_llm(r"exactly the same value", "true")
    assert direct_vm.run_validator() is True


def test_validator_rejects_diverging_severity(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_bob):
        contract.resolve_bounty(0)
    direct_vm.clear_mocks()
    setup_web_mocks(direct_vm)
    direct_vm.mock_llm(r"security judge", LOW_DECISION)
    direct_vm.mock_llm(r"exactly the same value", "false")
    assert direct_vm.run_validator() is False


def test_appeal_reruns_ai_and_updates_payout(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_bob):
        contract.resolve_bounty(0)

    with direct_vm.prank(direct_alice), direct_vm.expect_revert("only the hunter can appeal"):
        contract.appeal(0, "it was critical, funds were stealable")
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("appeal reason must not be empty"):
        contract.appeal(0, "  ")

    direct_vm.clear_mocks()
    setup_web_mocks(direct_vm)
    direct_vm.mock_llm(r"security judge", CRITICAL_DECISION)
    direct_vm.mock_llm(r"exactly the same value", "true")
    with direct_vm.prank(direct_bob):
        contract.appeal(0, "the bug allowed stealing funds, not just a crash")
    b = contract.get_bounty(0)
    assert b["resolved_severity"] == "critical"
    assert b["payout_amount"] == BUDGET * 50 // 100
    assert b["appeal_count"] == 1
    assert b["appeal_reason"] == "the bug allowed stealing funds, not just a crash"
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("appeal already used"):
        contract.appeal(0, "again")


def test_close_returns_leftover(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_alice), direct_vm.expect_revert("bounty is not resolved"):
        contract.close_bounty(0)
    with direct_vm.prank(direct_bob):
        contract.submit_pr(0, PR_URL)
    with direct_vm.prank(direct_alice):
        contract.confirm_merge(0)
    with direct_vm.prank(direct_bob):
        contract.resolve_bounty(0)
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("only the maintainer"):
        contract.close_bounty(0)
    with direct_vm.prank(direct_alice):
        contract.close_bounty(0)
    b = contract.get_bounty(0)
    assert b["status"] == "closed"
    assert b["total_budget"] - b["total_transferred"] == BUDGET * 70 // 100


def test_cancel_open_bounty(direct_vm, direct_deploy, direct_alice, direct_bob):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    with direct_vm.prank(direct_bob), direct_vm.expect_revert("only the maintainer"):
        contract.cancel_bounty(0)
    direct_vm.sender = direct_alice
    contract.cancel_bounty(0)
    assert contract.get_bounty(0)["status"] == "closed"
    with direct_vm.prank(direct_alice), direct_vm.expect_revert("bounty not found"):
        contract.cancel_bounty(5)


def test_get_bounty_shape(direct_vm, direct_deploy, direct_alice):
    contract = deploy_with_bounty(direct_vm, direct_deploy, direct_alice)
    b = contract.get_bounty(0)
    assert b["title"] == "Fix negative deposit crash"
    assert b["issue_url"] == ISSUE_URL
    assert b["pr_url"] == ""
    assert b["total_budget"] == BUDGET
    assert b["severity_rules"] == RULES
    assert b["status"] == "open"
    assert b["resolved_severity"] == ""
    assert b["payout_amount"] == 0
    assert b["appeal_count"] == 0
    assert str(b["maintainer"]).lower() == "0x" + bytes(direct_alice).hex()
    with direct_vm.expect_revert("bounty not found"):
        contract.get_bounty(3)
