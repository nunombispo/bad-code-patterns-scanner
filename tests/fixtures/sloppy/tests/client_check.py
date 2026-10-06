def check_fetch() -> None:
    assert fetch("https://example.com", verify=False)
