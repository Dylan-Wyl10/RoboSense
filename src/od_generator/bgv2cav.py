#!/usr/bin/env python3
"""
Deterministically convert exactly (rate * total_bgv) vehicles from:
    id   : bgvXXXX -> cavXXXX
    type : bgv -> cav

in a SUMO .rou.xml file.

Vehicle selection rule:
    id starts with bgv_prefix
"""

import argparse
import random
import xml.etree.ElementTree as ET
from pathlib import Path


def convert_bgv_vehicles(
    input_xml: str,
    output_xml: str,
    rate: float,
    bgv_prefix: str = "bgv",
    cav_prefix: str = "cav",
    bgv_type: str = "bgv",
    cav_type: str = "cav",
    seed: int | None = None,
):
    if not (0.0 <= rate <= 1.0):
        raise ValueError("Rate must be between 0 and 1.")

    if seed is not None:
        random.seed(seed)

    tree = ET.parse(input_xml)
    root = tree.getroot()

    # Step 1: collect candidate vehicles
    candidates = []
    for veh in root.iter("vehicle"):
        vid = veh.get("id", "")
        if vid.startswith(bgv_prefix):
            candidates.append(veh)

    total_bgv = len(candidates)
    target_count = round(total_bgv * rate)

    print(f"Total BGV vehicles found: {total_bgv}")
    print(f"Target number to convert: {target_count}")

    # Step 2: choose EXACT subset
    vehicles_to_convert = random.sample(candidates, target_count)

    # Step 3: apply conversion
    for veh in vehicles_to_convert:
        old_id = veh.get("id")
        suffix = old_id[len(bgv_prefix):]
        new_id = f"{cav_prefix}{suffix}"

        veh.set("id", new_id)

        # Convert type *only if* it matches bgv_type
        if veh.get("type") == bgv_type:
            veh.set("type", cav_type)

    # Step 4: save output
    out_path = Path(output_xml)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(out_path, encoding="utf-8", xml_declaration=True)

    print(f"Converted exactly:        {target_count}")
    print(f"Output written to:        {output_xml}")


def main():
    parser = argparse.ArgumentParser(
        description="Deterministically convert bgvXXXX → cavXXXX and type bgv → cav."
    )
    parser.add_argument("input_xml", help="Input SUMO route file (.rou.xml)")
    parser.add_argument("output_xml", help="Output modified route file")

    parser.add_argument(
        "--rate",
        type=float,
        default=0.1,
        help="Fraction of vehicles to convert (0–1)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--bgv-prefix",
        default="bgv",
        help='Prefix of IDs to convert (default: "bgv")',
    )
    parser.add_argument(
        "--cav-prefix",
        default="cav",
        help='Prefix of new IDs (default: "cav")',
    )
    parser.add_argument(
        "--bgv-type",
        default="bgv",
        help='Original vehicle type to convert (default: "bgv")',
    )
    parser.add_argument(
        "--cav-type",
        default="cav",
        help='New converted vehicle type (default: "cav")',
    )

    args = parser.parse_args()

    convert_bgv_vehicles(
        input_xml=args.input_xml,
        output_xml=args.output_xml,
        rate=args.rate,
        bgv_prefix=args.bgv_prefix,
        cav_prefix=args.cav_prefix,
        bgv_type=args.bgv_type,
        cav_type=args.cav_type,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
