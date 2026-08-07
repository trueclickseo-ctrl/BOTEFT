from quant_ai_trader.workflows.paper_readiness import run


def test_paper_readiness_workflow_never_auto_approves(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path); monkeypatch.delenv("SAXO_ACCOUNT_KEY", raising=False)
    result = run()
    assert result["ready"] is False and "operator approval required" in result["blockers"]


def test_paper_readiness_reads_account_key_from_dotenv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path); (tmp_path / ".env").write_text("SAXO_ACCOUNT_KEY=sim-key\n", encoding="utf-8")
    monkeypatch.delenv("SAXO_ACCOUNT_KEY", raising=False)
    assert run()["checks"]["account_key_configured"] is True
