import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import pytest
from xbrl_parser import extract_numeric_facts, reconstruct_dataframe

SAMPLE_XML = """
<xbrl xmlns="http://www.xbrl.org/2003/instance" xmlns:us-gaap="http://fasb.org/us-gaap/2020-01-31">
  <context id="I-2001">
    <entity>
      <identifier scheme="http://www.sec.gov/CIK">0000320193</identifier>
    </entity>
    <period>
      <instant>2023-06-30</instant>
    </period>
  </context>
  <unit id="U-Monetary">
    <measure>iso4217:USD</measure>
  </unit>
  <us-gaap:Assets contextRef="I-2001" unitRef="U-Monetary">1000000</us-gaap:Assets>
  <us-gaap:Liabilities contextRef="I-2001" unitRef="U-Monetary">500000</us-gaap:Liabilities>
  <us-gaap:Equity contextRef="I-2001" unitRef="U-Monetary">500000</us-gaap:Equity>
</xbrl>
"""

SAMPLE_XSD = """
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" targetNamespace="http://fasb.org/us-gaap/2020-01-31" xmlns:us-gaap="http://fasb.org/us-gaap/2020-01-31" elementFormDefault="qualified">
  <xs:group name="BalanceSheet">
    <xs:sequence>
      <xs:element ref="us-gaap:Assets"/>
      <xs:element ref="us-gaap:Liabilities"/>
      <xs:element ref="us-gaap:Equity"/>
    </xs:sequence>
  </xs:group>
  <xs:element name="Assets" type="xs:decimal"/>
  <xs:element name="Liabilities" type="xs:decimal"/>
  <xs:element name="Equity" type="xs:decimal"/>
</xs:schema>
"""

def test_extract_numeric_facts():
    facts = extract_numeric_facts(SAMPLE_XML)
    first = facts[0]
    assert first["element"] == "Assets"
    assert first["value"] == "1000000"
    assert first["contextRef"] == "I-2001"


def test_reconstruct_dataframe():
    df = reconstruct_dataframe(SAMPLE_XML, SAMPLE_XSD)
    assert list(df["element"]) == ["Assets", "Liabilities", "Equity"]
    assert df.loc[df.element == "Liabilities", "value"].iloc[0] == "500000"

