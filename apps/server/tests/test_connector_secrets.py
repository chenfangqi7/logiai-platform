from app.core.secrets import MASK, decrypt_config, encrypt_config, merge_config, redact_config


def test_connector_credentials_are_encrypted_and_redacted_recursively():
    config = {"token": "private-token", "headers": {"X-Custom": "private-header"}, "query_params": {"apiKey": "private-key", "page": 1},
              "request_body": {"auth": {"password": "private-password"}}}
    stored = encrypt_config(config)
    assert "private-token" not in str(stored)
    assert "private-key" not in str(stored)
    assert "private-password" not in str(stored)
    assert "private-header" not in str(stored)
    assert decrypt_config(stored) == config
    public = redact_config(stored)
    assert public["query_params"]["apiKey"] == MASK
    assert public["request_body"]["auth"]["password"] == MASK
    assert public["headers"]["X-Custom"] == MASK
    merged = merge_config(config, {"token": MASK, "headers": {"X-Custom": MASK}, "query_params": {"apiKey": MASK, "page": 2}})
    assert merged["token"] == "private-token"
    assert merged["query_params"] == {"apiKey": "private-key", "page": 2}
    assert merged["headers"] == {"X-Custom": "private-header"}
