# Recombination screen: what the PhiPack output supports

`phipack.txt` is the unedited PhiPack output from the 15-sequence alignment.
The screen was run on the earlier alignment version (3,221 columns, 533
parsimony-informative sites). The committed alignment has 535 informative
sites, so the screen was not rerun after the final consensus patch. The output
is kept as a record of the earlier check, not as a final result.

## Numbers in the output

| Test | Value in `phipack.txt` | Reading |
|---|---|---|
| PHI (permutation) | 0.00e+00 | below the 1,000-permutation resolution; report as p < 0.001 |
| NSS | 0.00e+00 | below the 1,000-permutation resolution; report as p < 0.001 |
| Max χ² | 2.80e-02 | p = 0.028; this would not survive a Bonferroni correction for three tests at α = 0.05 (0.0167) |

The best Max χ² breakpoint is reported between `NC_003977.2` and
`HBV_D_B364_2014`, both genotype D.

## Why this is not a recombination claim

- **The panel spans genotypes A–F.** PhiPack's tests assume a single
  recombining population. Here the estimated pairwise diversity is 8.9%, most of
  which separates genotypes. A signal can reflect that structure rather than
  recombination within a lineage.
- **Two genomes are partial.** B575/2014 is 34.9% `N` and B364/2014 is 16.9%
  `N`. Missing data can inflate PHI and related statistics.
- **The alignment has two gap-rich blocks.** Positions 2,356–2,361 and
  2,863–2,895 have more than 50% gaps. They were retained, not trimmed, so the
  alignment around those blocks is uncertain.
- **A statistical signal is not a breakpoint.** No recombinant breakpoint,
  parent or transmission event is claimed here.

## What would make the screen stronger

1. Run the test within one genotype (for example, the five genotype D genomes
   or the four genotype A genomes), where the single-population assumption is
   more plausible.
2. Mask the two gap-rich blocks and rerun, then check whether the signal
   persists.
3. Use a recombination-aware phylogenetic method and report the uncertainty of
   any breakpoint.
4. Treat the result as a hypothesis to test with longer reads or cloned
   sequences, not as a conclusion from five short-read consensus genomes.

None of these follow-up steps are part of the committed results.
