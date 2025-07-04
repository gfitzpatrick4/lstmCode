import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))


from xbrl_parser import parse_xbrl_files



def test_parse_xbrl_files():
    df = parse_xbrl_files("tests/xml_test.txt", "tests/xsd_test.txt")
    assert not df.empty
    assert {
        "label",
        "footnotes",
        "references",
        "presentation_parents",
        "calculation_parents",
        "definition_parents",
        "presentation_roles",
        "calculation_roles",
        "definition_roles",
    }.issubset(df.columns)
    assert df["footnotes"].dropna().astype(bool).any()


if __name__ == "__main__":
    dataframe = parse_xbrl_files("tests/xml_test.txt", "tests/xsd_test.txt")

    def _print_section(keyword: str) -> None:
        target = keyword.lower().replace(" ", "")

        def contains_keyword(roles):
            if not isinstance(roles, list):
                return False
            return any(target in (r or "").lower().replace(" ", "") for r in roles)


        subset = dataframe[dataframe["presentation_roles"].apply(contains_keyword)]
        print(f"\n=== {keyword.title()} ===")
        print(subset[["element", "value", "label"]])

    _print_section("balance")
    _print_section("cash flow")
    _print_section("income")
