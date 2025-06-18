
from typing import List, Dict
from lxml import etree
import pandas as pd


def extract_numeric_facts(xbrl_xml: str) -> List[Dict[str, str]]:
    """Extract numeric facts from an XBRL XML string.

    Returns a list of dictionaries with keys ``element``, ``value``,
    ``contextRef``, ``unitRef`` and ``decimals`` for each numeric fact.
    """
    root = etree.fromstring(xbrl_xml.encode("utf-8"))
    facts: List[Dict[str, str]] = []

    for elem in root.iter():
        if "contextRef" in elem.attrib and elem.text and elem.text.strip():
            value = elem.text.strip()
            # Basic check that value looks numeric
            try:
                float(value.replace(",", ""))
            except ValueError:
                continue

            facts.append({
                "element": etree.QName(elem).localname,
                "value": value,
                "contextRef": elem.attrib.get("contextRef"),
                "unitRef": elem.attrib.get("unitRef"),
                "decimals": elem.attrib.get("decimals"),
            })

    return facts


def parse_xbrl_file(path: str) -> List[Dict[str, str]]:
    """Parse an XBRL file from ``path`` and return numeric facts."""
    with open(path, "r", encoding="utf-8") as fh:
        xml = fh.read()
    return extract_numeric_facts(xml)


def _parse_xsd_order(xsd_xml: str) -> List[str]:
    """Extract element ordering from an XSD schema.

    This is a simplified parser that looks for ``xs:sequence`` elements and
    returns the referenced element names in the order they appear.
    """
    schema = etree.fromstring(xsd_xml.encode("utf-8"))
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    order: List[str] = []

    for seq in schema.findall(".//xs:sequence", namespaces=ns):
        for el in seq.findall("xs:element", namespaces=ns):
            ref = el.get("ref")
            name = el.get("name")
            if ref:
                name = ref.split(":")[-1]
            if name:
                order.append(name)

    if not order:
        for el in schema.findall(".//xs:element", namespaces=ns):
            name = el.get("name")
            if name:
                order.append(name)

    seen = set()
    unique_order = []
    for n in order:
        if n not in seen:
            unique_order.append(n)
            seen.add(n)
    return unique_order


def reconstruct_dataframe(xbrl_xml: str, xsd_xml: str) -> pd.DataFrame:
    """Return a ``DataFrame`` of numeric facts ordered according to ``xsd_xml``."""
    facts = extract_numeric_facts(xbrl_xml)
    df = pd.DataFrame(facts)
    if df.empty:
        return df

    order = _parse_xsd_order(xsd_xml)
    order_index = {name: idx for idx, name in enumerate(order)}
    df["order"] = df["element"].map(order_index)
    df.sort_values("order", inplace=True)
    df.drop(columns="order", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def parse_xbrl_files(xml_path: str, xsd_path: str) -> pd.DataFrame:
    """Parse XBRL XML and XSD files and return a reconstructed DataFrame."""
    with open(xml_path, "r", encoding="utf-8") as fh:
        xml = fh.read()
    with open(xsd_path, "r", encoding="utf-8") as fh:
        xsd = fh.read()
    return reconstruct_dataframe(xml, xsd)

