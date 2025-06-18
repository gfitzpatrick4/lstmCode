

from typing import List, Dict, Any, Set, Optional

from lxml import etree
import pandas as pd


def _strip_prefix(name: Optional[str]) -> Optional[str]:
    """Return local element name without namespace prefix."""
    if not name:
        return name
    if "_" in name:
        return name.split("_", 1)[1]
    if ":" in name:
        return name.split(":", 1)[1]
    return name


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
                "id": elem.attrib.get("id"),
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


def _parse_footnotes(xbrl_xml: str) -> Dict[str, List[str]]:
    """Return mapping of fact ``id`` to list of associated footnotes."""
    ns = {
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
        "xhtml": "http://www.w3.org/1999/xhtml",
    }
    root = etree.fromstring(xbrl_xml.encode("utf-8"))
    footnotes: Dict[str, List[str]] = {}

    for fn_link in root.findall(".//link:footnoteLink", namespaces=ns):
        locators = {
            loc.get("{http://www.w3.org/1999/xlink}label"): loc.get("{http://www.w3.org/1999/xlink}href").lstrip("#")
            for loc in fn_link.findall("link:loc", namespaces=ns)
        }
        notes = {
            note.get("{http://www.w3.org/1999/xlink}label"): "".join(note.itertext()).strip()
            for note in fn_link.findall("link:footnote", namespaces=ns)
        }
        for arc in fn_link.findall("link:footnoteArc", namespaces=ns):
            from_lbl = arc.get("{http://www.w3.org/1999/xlink}from")
            to_lbl = arc.get("{http://www.w3.org/1999/xlink}to")
            fact_id = locators.get(from_lbl)
            note_text = notes.get(to_lbl)
            if fact_id and note_text:
                footnotes.setdefault(fact_id, []).append(note_text)

    return footnotes


def _parse_label_linkbase(xsd_xml: str) -> Dict[str, str]:
    """Return concept to label mapping from ``labelLink`` elements."""
    ns = {
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    root = etree.fromstring(xsd_xml.encode("utf-8"))
    labels: Dict[str, str] = {}

    for lb in root.findall(".//link:labelLink", namespaces=ns):
        loc_map = {

            loc.get("{http://www.w3.org/1999/xlink}label"): _strip_prefix(
                loc.get("{http://www.w3.org/1999/xlink}href").split("#")[-1]
            )

            for loc in lb.findall("link:loc", namespaces=ns)
        }
        resources = {
            res.get("{http://www.w3.org/1999/xlink}label"): "".join(res.itertext()).strip()
            for res in lb.findall("link:label", namespaces=ns)
        }
        for arc in lb.findall("link:labelArc", namespaces=ns):
            concept = loc_map.get(arc.get("{http://www.w3.org/1999/xlink}from"))
            label = resources.get(arc.get("{http://www.w3.org/1999/xlink}to"))
            if concept and label and concept not in labels:
                labels[concept] = label

    return labels


def _parse_reference_linkbase(xsd_xml: str) -> Dict[str, List[str]]:
    """Return concept to list of reference strings from ``referenceLink``."""
    ns = {
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
        "xhtml": "http://www.w3.org/1999/xhtml",
    }
    root = etree.fromstring(xsd_xml.encode("utf-8"))
    refs: Dict[str, List[str]] = {}

    for ref_link in root.findall(".//link:referenceLink", namespaces=ns):
        loc_map = {

            loc.get("{http://www.w3.org/1999/xlink}label"): _strip_prefix(
                loc.get("{http://www.w3.org/1999/xlink}href").split("#")[-1]
            )

            for loc in ref_link.findall("link:loc", namespaces=ns)
        }
        resources = {
            res.get("{http://www.w3.org/1999/xlink}label"): "".join(res.itertext()).strip()
            for res in ref_link.findall("link:reference", namespaces=ns)
        }
        for arc in ref_link.findall("link:referenceArc", namespaces=ns):
            concept = loc_map.get(arc.get("{http://www.w3.org/1999/xlink}from"))
            text = resources.get(arc.get("{http://www.w3.org/1999/xlink}to"))
            if concept and text:
                refs.setdefault(concept, []).append(text)

    return refs


def _parse_roles(xsd_xml: str) -> Dict[str, str]:
    """Return mapping of role ``id`` to definition string."""
    ns = {"link": "http://www.xbrl.org/2003/linkbase"}
    root = etree.fromstring(xsd_xml.encode("utf-8"))
    roles: Dict[str, str] = {}
    for rt in root.findall('.//link:roleType', namespaces=ns):
        role_id = rt.get('id')
        def_el = rt.find('link:definition', namespaces=ns)
        definition = ''.join(def_el.itertext()).strip() if def_el is not None else ''
        if role_id:
            roles[role_id] = definition
    return roles


def _parse_arcs(root: etree._Element, link_name: str, arc_name: str) -> List[Dict[str, Any]]:
    ns = {
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
    }
    arcs: List[Dict[str, Any]] = []
    for link in root.findall(f".//link:{link_name}", namespaces=ns):
        role = link.get("{http://www.w3.org/1999/xlink}role")
        loc_map = {
            loc.get("{http://www.w3.org/1999/xlink}label"): _strip_prefix(
                loc.get("{http://www.w3.org/1999/xlink}href").split("#")[-1]
            )

            for loc in link.findall("link:loc", namespaces=ns)
        }
        for arc in link.findall(f"link:{arc_name}", namespaces=ns):
            from_lbl = arc.get("{http://www.w3.org/1999/xlink}from")
            to_lbl = arc.get("{http://www.w3.org/1999/xlink}to")
            arcs.append(
                {
                    "from": loc_map.get(from_lbl),
                    "to": loc_map.get(to_lbl),
                    "order": arc.get("order"),
                    "arcrole": arc.get("{http://www.w3.org/1999/xlink}arcrole"),
                    "role": role,
                }
            )
    return arcs


def _parse_linkbases(xbrl_xml: str, xsd_xml: str) -> Dict[str, Any]:
    """Parse footnotes and various linkbases from XML and XSD."""
    linkbases: Dict[str, Any] = {}
    linkbases["footnotes"] = _parse_footnotes(xbrl_xml)

    root = etree.fromstring(xsd_xml.encode("utf-8"))
    linkbases["labels"] = _parse_label_linkbase(xsd_xml)
    linkbases["references"] = _parse_reference_linkbase(xsd_xml)
    linkbases["roles"] = _parse_roles(xsd_xml)
    linkbases["presentation"] = _parse_arcs(root, "presentationLink", "presentationArc")
    linkbases["calculation"] = _parse_arcs(root, "calculationLink", "calculationArc")
    linkbases["definition"] = _parse_arcs(root, "definitionLink", "definitionArc")
    return linkbases


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

    linkbases = _parse_linkbases(xbrl_xml, xsd_xml)

    df["label"] = df["element"].map(linkbases.get("labels", {}))
    df["footnotes"] = df["id"].map(linkbases.get("footnotes", {}))
    df["references"] = df["element"].map(linkbases.get("references", {}))

    roles = linkbases.get("roles", {})

    def _to_lookup(arcs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        lookup: Dict[str, List[str]] = {}
        for arc in arcs:
            parent = arc.get("from")
            child = arc.get("to")
            if parent and child:
                lookup.setdefault(child, []).append(parent)
        return lookup

    def _role_lookup(arcs: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        lookup: Dict[str, Set[str]] = {}
        for arc in arcs:
            child = arc.get("to")
            role = arc.get("role")
            if child and role:
                lookup.setdefault(child, set()).add(role)
        return {k: list(v) for k, v in lookup.items()}

    df["presentation_parents"] = df["element"].map(
        _to_lookup(linkbases.get("presentation", []))
    )
    df["calculation_parents"] = df["element"].map(
        _to_lookup(linkbases.get("calculation", []))
    )
    df["definition_parents"] = df["element"].map(
        _to_lookup(linkbases.get("definition", []))
    )

    df["presentation_roles"] = df["element"].map(
        _role_lookup(linkbases.get("presentation", []))
    ).map(
        lambda roles_list: [roles.get(r.split("#")[-1], r) for r in roles_list] if isinstance(roles_list, list) else roles_list
    )

    df["calculation_roles"] = df["element"].map(
        _role_lookup(linkbases.get("calculation", []))
    ).map(
        lambda roles_list: [roles.get(r.split("#")[-1], r) for r in roles_list] if isinstance(roles_list, list) else roles_list
    )

    df["definition_roles"] = df["element"].map(
        _role_lookup(linkbases.get("definition", []))
    ).map(
        lambda roles_list: [roles.get(r.split("#")[-1], r) for r in roles_list] if isinstance(roles_list, list) else roles_list
    )

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

