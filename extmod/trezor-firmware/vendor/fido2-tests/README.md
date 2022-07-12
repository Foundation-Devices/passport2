# fido2-tests

Test suite for FIDO2, U2F, and other security key functions

# Setup

Need python 3.6+.

`make venv` and `source venv/bin/activate`

Or simply `pip3 install --user -r requirements.txt`

# Running the tests

Run all FIDO2, U2F, and HID tests:

```
pytest tests/standard -s
```

Run vendor/model specific tests:

```
pytest tests/vendor -s
```

Run subset of tests with `-k` flag, example:
```
pytest -k "getinfo or hmac_secret" -s
```

To run tests via nfc, supply the `--nfc` option.
Make sure that you have `pyscard` python module installed properly and have updated `python-fido2` (by Yubikey) library to lastest version

```
pytest --nfc tests/standard -s
```

Note that in most cases when testing a hardware authenticator, `-s` must be supplied to disable stdin/stdout capturing.  This is so the prompts to power cycle the authenticator can be seen and continued.

# Running against simulation

To run tests against a "simulation" build of the Solo authenticator, supply the `--sim` option.

```
pytest --sim tests/standard
```

All tests should pass without having to use `-s` or provide any interaction.

# Notes

Initial SoloKeys models truncates the displayName, which causes a couple of the tests to fail.
To succeed all tests, pass `--vendor solokeys` as an option.

# Contributing

We use `black` and `isort` to prevent code formatting discussions.

The `make venv` setup method installs git pre-commit hooks that check conformance automatically.

You can also `make check` and `make fix` manually, or use an editor plugins.

# License

Apache-2.0 OR MIT

