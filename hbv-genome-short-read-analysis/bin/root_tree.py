#!/usr/bin/env python3
"""Root an IQ-TREE Newick file on a chosen outgroup, preserving branch lengths."""

import argparse

from Bio import Phylo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tree", required=True)
    parser.add_argument("--outgroup", default="MK183647.1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    tree = Phylo.read(args.tree, "newick")
    outgroup = next(
        (terminal for terminal in tree.get_terminals() if terminal.name.startswith(args.outgroup)),
        None,
    )
    if outgroup is None:
        raise SystemExit(f"outgroup {args.outgroup} not found in tree")
    tree.root_with_outgroup(outgroup)
    Phylo.write(tree, args.out, "newick")
    print(f"rooted on {outgroup.name} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
