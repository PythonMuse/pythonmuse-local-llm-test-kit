"""The calculator part. The model retrieves; Python adds up.

Outstanding shares are summed here from the cap table, never asked of the
model. The cross-check compares the preferred shares the model extracted from
the financing agreement against the cap table's row for that series.
"""

import csv

OUTSTANDING = "Issued and outstanding"


def _shares(text):
    return int(str(text).replace(",", "").strip())


def read_cap_table(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def outstanding_shares(path):
    """Sum of issued-and-outstanding shares. Reserved option-pool shares are
    excluded because they have not been issued."""
    return sum(_shares(r["shares"]) for r in read_cap_table(path)
               if r["status"] == OUTSTANDING)


def series_shares(path, series_name):
    for r in read_cap_table(path):
        if r["share_class"] == series_name:
            return _shares(r["shares"])
    raise KeyError(f"{series_name} not found in {path}")


def cap_table_check(path, series_name, extracted_preferred):
    """Compare the model's extracted preferred share count with the cap table.

    Returns a dict with status TIES, BREAK, or NOT_CHECKED (when the model did
    not return a usable number). A TIES result is only as good as the
    extraction it was built on -- which is why the scorer exists.
    """
    on_cap_table = series_shares(path, series_name)
    if extracted_preferred is None:
        return {"cap_table_preferred": on_cap_table, "extracted_preferred": None,
                "difference": None, "status": "NOT_CHECKED"}
    diff = extracted_preferred - on_cap_table
    return {"cap_table_preferred": on_cap_table,
            "extracted_preferred": extracted_preferred,
            "difference": diff,
            "status": "TIES" if diff == 0 else "BREAK"}
