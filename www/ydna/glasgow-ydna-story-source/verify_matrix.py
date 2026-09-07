#!/usr/bin/env python3
"""Reproduce the seven-kit distance audit without third-party dependencies.

This analyses the supplied distance matrix, NOT raw STR rows or DNA reads.
Zero distances between distinct kits are retained. MSTs are counted on the
labelled modern kits, not on collapsed haplotypes or historical ancestors.

Usage: python3 verify_matrix.py [data.json] [--output matrix-audit.json]
"""
import argparse
import itertools
import json
from pathlib import Path
from typing import List, Tuple

Edge = Tuple[int, int, float]


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def join(self, a: int, b: int) -> bool:
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        self.parent[a] = b
        return True


def audit_matrix(data: dict) -> dict:
    ids, matrix = data['audit']['ids'], data['audit']['matrix']
    n = len(ids)
    if n < 2 or n > 8:
        raise ValueError('This exhaustive verifier is intended for 2–8 kits.')
    if len(set(ids)) != n or len(matrix) != n or any(len(row) != n for row in matrix):
        raise ValueError('Expected unique kit IDs and a square matrix.')
    if any(not isinstance(v, (int, float)) or v < 0 for row in matrix for v in row):
        raise ValueError('Distances must be non-negative numbers.')
    if any(matrix[i][i] != 0 for i in range(n)):
        raise ValueError('The matrix diagonal must be zero.')
    if any(matrix[i][j] != matrix[j][i] for i in range(n) for j in range(n)):
        raise ValueError('The matrix must be symmetric.')
    triangle_failures = []
    for a, b, c in itertools.permutations(range(n), 3):
        if matrix[a][c] > matrix[a][b] + matrix[b][c]:
            triangle_failures.append([ids[a], ids[b], ids[c]])
    quartet_failures = []
    for a, b, c, d in itertools.combinations(range(n), 4):
        sums = [matrix[a][b] + matrix[c][d],
                matrix[a][c] + matrix[b][d],
                matrix[a][d] + matrix[b][c]]
        ordered = sorted(sums)
        if ordered[-1] != ordered[-2]:
            quartet_failures.append({'kits': [ids[x] for x in (a, b, c, d)],
                                      'pairing_sums': sums})
    edges: List[Edge] = [(i, j, matrix[i][j])
                         for i, j in itertools.combinations(range(n), 2)]
    # Kruskal obtains the optimum before exhaustive tie enumeration.
    uf, optimum, accepted = UnionFind(n), 0, 0
    for a, b, weight in sorted(edges, key=lambda e: e[2]):
        if uf.join(a, b):
            optimum += weight
            accepted += 1
            if accepted == n - 1:
                break
    trees = []
    for selected in itertools.combinations(edges, n - 1):
        if sum(edge[2] for edge in selected) != optimum:
            continue
        uf = UnionFind(n)
        if all(uf.join(a, b) for a, b, _ in selected):
            trees.append([[ids[a], ids[b], w] for a, b, w in selected])
    # Every accepted n−1-edge acyclic graph on n vertices is connected.
    return {
        'scope': 'Supplied endpoint distance matrix; no raw-genotype reanalysis',
        'kits': ids,
        'unique_pairs': len(edges),
        'symmetric': True,
        'triangle_failures': triangle_failures,
        'quartets_tested': len(list(itertools.combinations(range(n), 4))),
        'quartet_failures': quartet_failures,
        'minimum_spanning_weight': optimum,
        'minimum_spanning_tree_count': len(trees),
        'minimum_spanning_trees': trees,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', nargs='?', type=Path,
                        default=Path(__file__).resolve().parent / 'data.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.data.read_text(encoding='utf-8'))
        result = audit_matrix(data)
        expected = data['audit']
        checks = {
            'MST weight matches the page': result['minimum_spanning_weight'] == expected['mstWeight'],
            'MST count matches the page': result['minimum_spanning_tree_count'] == expected['mstCount'],
            'Quartet failure count matches': len(result['quartet_failures']) == expected['fourPointViolations'],
            'No triangle inequality failures': not result['triangle_failures'],
        }
        result['page_checks'] = checks
        rendered = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + '\n', encoding='utf-8')
        print(rendered)
        if not all(checks.values()):
            parser.exit(2, '\nComputed values do not match the embedded page summary.\n')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f'Audit failed: {exc}\n')


if __name__ == '__main__':
    main()
