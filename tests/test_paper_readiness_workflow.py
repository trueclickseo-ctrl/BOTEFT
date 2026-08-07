from quant_ai_trader.workflows.paper_readiness import run


def test_paper_readiness_workflow_never_auto_approves(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path); monkeypatch.delenv("SAXO_ACCOUNT_KEY", raising=False)
    result = run()
    assert result["ready"] is False and "operator approval required" in result["blockers"]
