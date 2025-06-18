# LSTM Code

This repository includes an XBRL parser and related tests.

## Running Tests

Install the dependencies and run pytest:

```bash
pip install -r requirements.txt -q
pytest -q
```

To see example output for the balance sheet, cash flow, and income statement sections, execute the test script directly:

```bash
python tests/test_xbrl_parser.py
```
