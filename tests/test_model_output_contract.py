from vlm_contract import parse_target_exact


def test_exact_tokens_are_accepted():
    assert parse_target_exact("RED") == "RED"
    assert parse_target_exact(" blue \n") == "BLUE"
    assert parse_target_exact("NONE") == "NONE"


def test_prose_and_substrings_are_rejected():
    bad = [
        "NOT RED",
        "NONE, because RED is absent",
        "BLUE or RED",
        "CREDIT",
        "RED.",
        '{"target":"RED"}',
        "",
    ]

    for value in bad:
        assert parse_target_exact(value) is None
