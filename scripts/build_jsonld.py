"""Generate the JSON-LD context and the JSON-LD versions of every Turtle file.

Usage (from the repository root):
    python scripts/build_jsonld.py

The context gives a compact name to every class, property and vocabulary term
of the ontology. Each Turtle file is serialised to JSON-LD with that context
inlined, then parsed back and checked for isomorphism with the source graph.
"""

import json
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, Graph
from rdflib.compare import isomorphic

ROOT = Path(__file__).resolve().parent.parent
HCTA = "https://example.org/hcta#"

SOURCES = [
    ROOT / "ontology" / "hcta-ontology.ttl",
    ROOT / "shapes" / "hcta-shapes.ttl",
    ROOT / "examples" / "hcta-example-soybean.ttl",
]


def local(iri):
    return str(iri)[len(HCTA):]


def build_context(onto: Graph) -> dict:
    ctx = {
        "@version": 1.1,
        "hcta": HCTA,
        "ex": "https://example.org/hcta/example/",
        "owl": str(OWL),
        "rdf": str(RDF),
        "rdfs": str(RDFS),
        "xsd": str(XSD),
        "skos": "http://www.w3.org/2004/02/skos/core#",
        "prov": "http://www.w3.org/ns/prov#",
        "time": "http://www.w3.org/2006/time#",
        "dcterms": "http://purl.org/dc/terms/",
        "sh": "http://www.w3.org/ns/shacl#",
        "hctash": "https://example.org/hcta/shapes#",
        "id": "@id",
        "type": "@type",
        "label": "rdfs:label",
        "prefLabel": "skos:prefLabel",
        "comment": "rdfs:comment",
    }
    for cls in set(onto.subjects(RDF.type, OWL.Class)):
        if str(cls).startswith(HCTA):
            ctx[local(cls)] = f"hcta:{local(cls)}"
    for prop in set(onto.subjects(RDF.type, OWL.ObjectProperty)):
        if str(prop).startswith(HCTA):
            ctx[local(prop)] = {"@id": f"hcta:{local(prop)}", "@type": "@id"}
    for prop in set(onto.subjects(RDF.type, OWL.DatatypeProperty)):
        if not str(prop).startswith(HCTA):
            continue
        term = {"@id": f"hcta:{local(prop)}"}
        rng = onto.value(prop, RDFS.range)
        if rng is not None and str(rng).startswith(str(XSD)) and rng != XSD.string:
            term["@type"] = "xsd:" + str(rng)[len(str(XSD)):]
        ctx[local(prop)] = term
    # Individuals of the controlled vocabularies
    for ind, _, cls in onto.triples((None, RDF.type, None)):
        if (
            str(ind).startswith(HCTA)
            and (cls, RDF.type, OWL.Class) in onto
            and (ind, RDF.type, OWL.Class) not in onto
        ):
            ctx.setdefault(local(ind), f"hcta:{local(ind)}")
    return ctx


def main():
    onto = Graph().parse(SOURCES[0], format="turtle")
    ctx = build_context(onto)
    ctx_path = ROOT / "context" / "hcta-context.jsonld"
    ctx_path.write_text(json.dumps({"@context": ctx}, indent=2, ensure_ascii=False))
    print(f"{ctx_path.relative_to(ROOT)}: {len(ctx)} terms")

    for src in SOURCES:
        g = Graph().parse(src, format="turtle")
        out = g.serialize(format="json-ld", context=ctx, auto_compact=True, indent=2)
        dst = src.with_suffix(".jsonld")
        dst.write_text(out)
        back = Graph().parse(data=out, format="json-ld")
        ok = isomorphic(g, back)
        print(f"{dst.relative_to(ROOT)}: {len(g)} triples, round trip isomorphic={ok}")
        if not ok:
            raise SystemExit(f"Round trip failed for {src.name}")


if __name__ == "__main__":
    main()
