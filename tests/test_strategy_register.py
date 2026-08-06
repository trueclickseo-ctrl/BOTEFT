from pathlib import Path

def test_strategy_research_register_exists():
    text = Path("STRATEGY_RESEARCH.md").read_text(encoding="utf-8")
    assert "AI target-before-stop" in text
    assert "Momentum baseline" in text
