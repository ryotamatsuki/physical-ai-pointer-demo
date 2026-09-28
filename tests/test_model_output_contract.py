from modal_backend import _parse_target_exact


def test_exact_tokens_are_accepted():
    assert _parse_target_exact("RED") == "RED"
    assert _parse_target_exact(" blue \n") == "BLUE"
    assert _parse_target_exact("NONE") == "NONE"


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
        assert _parse_target_exact(value) is None
