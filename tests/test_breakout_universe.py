from quant_ai_trader.data.database import MarketDataRepository
from quant_ai_trader.workflows.breakout_universe import run


def test_universe_breakout_comparison_is_research_only(tmp_path, sample_bars, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repo = MarketDataRepository("data/quant_ai_trader.sqlite3")
    repo.initialize()
    repo.upsert_bars("SPY", sample_bars)
    repo.upsert_bars("QQQ", sample_bars)

    result = run(["QQQ"])

    assert result["universe_size"] == 1
    assert result["paper_trading_approved"] is False
    assert result["results"][0]["symbol"] == "QQQ"
    assert result["results"][0]["verdict"] in {
        "does_not_beat_benchmark",
        "insufficient_evidence_despite_benchmark_outperformance",
        "candidate_does_not_beat_benchmark",
        "research_candidate_beats_benchmark",
    }
