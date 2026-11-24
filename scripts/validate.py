"""Validate the example data against the HCTA ontology and SHACL shapes.

Usage (from the repository root):
    python scripts/validate.py              # validate the example as it is
    python scripts/validate.py --break      # also break five invariants in a copy and check they are caught

Expected result for the example: conforms, with exactly one warning
(the sale B quality claim notice is an orphan obligation, on purpose).
"""

import re
import sys
from pathlib import Path

from pyshacl import validate
from rdflib import XSD, Graph, Literal, Namespace

ROOT = Path(__file__).resolve().parent.parent
H = Namespace("https://example.org/hcta#")
E = Namespace("https://example.org/hcta/example/")


def load():
    onto = Graph().parse(ROOT / "ontology" / "hcta-ontology.ttl", format="turtle")
    shapes = Graph().parse(ROOT / "shapes" / "hcta-shapes.ttl", format="turtle")
    data = Graph().parse(ROOT / "examples" / "hcta-example-soybean.ttl", format="turtle")
    return onto, shapes, data


def run(data, shapes, onto):
    conforms, _, text = validate(
        data,
        shacl_graph=shapes,
        ont_graph=onto,
        inference="rdfs",
        allow_warnings=True,
        advanced=True,
    )
    messages = sorted(set(re.findall(r"Message: (.*)", text)))
    return conforms, messages


def main():
    onto, shapes, data = load()
    conforms, messages = run(data, shapes, onto)
    print(f"Example data conforms (warnings allowed): {conforms}")
    for m in messages:
        print(f"  - {m}")

    if "--break" in sys.argv:
        broken = Graph()
        for t in data:
            broken.add(t)
        broken.remove((E["Att-SaleB"], None, None))  # I1
        broken.remove((E["Ev-BL"], H.transactionTime, None))  # I3
        broken.remove((E["AI-Prop-SaB-Laytime"], H.validatedBy, None))  # I4
        broken.add((E["SaleB"], H.legacyKey, Literal("TRD-778812")))  # I5
        broken.set((E["Inc-SaB-FOSFA"], H.resolutionDate, Literal("2023-01-01", datatype=XSD.date)))  # I6
        conforms, messages = run(broken, shapes, onto)
        print(f"\nBroken copy conforms: {conforms}")
        for m in messages:
            print(f"  - {m}")


if __name__ == "__main__":
    main()
