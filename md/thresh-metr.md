# Thresh Metr MuSig

This document discusses approaches to express THRESHold spending policies with MErkle TRees and MuSig.

## Introduction

There are multiple ways to set up a t-of-n threshold spending policy with Taproot.
The most space efficient and private option is to use a threshold signature scheme like FROST to create a single public key and use that as the Taproot output key.
No script spending and therefore no Taproot Merkle tree needed.
However, threshold signatures are not always an option.
For example, because storing the key shares is inconvenient, threshold signing isn't robust in general or simply because no suitable threshold implementation exists.

It is well known that a t-of-n threshold policy can also be implemented with a Taproot tree of t-of-t spending policies.

For example, a 2-of-3 policy can be expressed as a disjunction of three conjunctions:
```
2-of-{Alice, Bob, Charlie} = (Alice and Bob) or (Alice and Charlie) or (Bob and Charlie)
```

Using MuSig key aggregation, one can build a Taproot tree for this policy as follows:
```
KeyAgg(A, B)
|           \
|            \
|             \
KeyAgg(A, C)   KeyAgg(B, C)
```
where the root is the Taproot output key and the leaf public keys are committed to the Merkle Tree along with the `OP_CHECKSIGVERIFY` opcode.

Compared to a `CHECKSIGADD`-based solution that always requires two signatures of three public keys, the advantage of this approach is better fungibility and efficiency.

We call a tree representing a t-of-n threshold policy *fully MuSig merkleized* if it purely consists of t-of-t spending conditions.
The problem with such a tree is that the number of t-of-t conditions grows quickly (Example: n = 15, t = 11, "n choose t" = 15504).
As a result the Merkle proofs become large for practical purposes (Example: log_2("n choose t") = 13).
Moreover, in order to minimize the time to obtain a signature one is required to run the MuSig protocol for all t-of-t spending conditions in parallel, which is a large number in a fully MuSig merkleized tree.

## Assumption: Only up to k signers are non-cooperative most of the time

One idea to mitigate these issues comes from the observation that in many scenarios more than t parties are willing to sign.
If we can bound the number of non-cooperative signers to be no more than some k < n - t, we can create a much more efficient spending tree, which we call *k MuSig merkleized*.

To set up such a tree, we start by creating a worst case spending condition, which is just a script with n public keys and a `CHECKSIGADD` opcode that requires t signatures.
This is used as a fall back if more than k signers are non-cooperative.
As in the case of fully MuSig merkleized trees, the remaining spending paths consist of *t-combinations* (combinations of size t) of the n public keys.

Now, knowing that only up to k signers are non-cooperative and we have a fall back in the form of a `CHECKSIGADD` path, we do not need all "n choose t"-many combinations in the tree.
For example, a 3-of-5 threshold policy has t-combinations c0 = (0, 1, 2), c1 = (2, 3, 4), c2 = (1, 2, 3), etc.
With k = 1 however, combination c2 is redundant.
It would only be useful if signer 0 or signer 4 is absent, but in the former case we can use c1 and in the latter c2.

Let us define how a k MuSig merkleized tree for a t-of-n threshold looks like in general:
- Let C be the t-combinations of n public keys.
- Let D be the k-combinations of n public keys.
- Let Cp be the smallest subset of C such that for all d in D there exists c in Cp such that the intersection of c and d is empty.

We want the MuSig key aggregate of every combination in Cp to appear in the tree.
There are multiple ways to lay out the tree.
For example, one of the combinations can be used as the taproot output key, the `CHECKSIGADD` fall back is a child of the and the rest of the combinations are arranged as a balanced tree that is the second child of the root key.

```
KeyAgg(c in Cp)
|              \
|               \
|                \
fall back script  balanced tree of KeyAgg(c') for all c' in Cp\{c}
```

The (inefficient and non-optimal) algorithm [thresh-metr.py](thresh-metr.py) gives the following output, demonstrating that k MuSig merkleized trees offer significant improvements over fully merkleized trees:

- 3-of-5 with up to 1 signers non-cooperative
  - Parallel signing sessions: 4
  - Everyone in key path cooperative: 1 sig: 64 WU
  - Up to 1 non-cooperative:         1 sig, 1 pk, 2 deep: 160 WU
  - More than 1 non-cooperative:     3 sig, 5 pk, 1 deep: 384 WU
  - In Comparison, fully merkleized multisig (6 parallel sessions): 1 sig, 1 pk, 4 deep: 224 WU
- 11-of-15 with up to 2 signers non-cooperative
  - Parallel signing sessions: 32
  - Everyone in key path cooperative: 1 sig: 64 WU
  - Up to 2 non-cooperative:         1 sig, 1 pk, 6 deep: 288 WU
  - More than 2 non-cooperative:     11 sig, 15 pk, 1 deep: 1216 WU
  - In Comparison, fully merkleized multisig (1001 parallel sessions): 1 sig, 1 pk, 11 deep: 448 WU
- 15-of-20 with up to 2 signers non-cooperative
  - Parallel signing sessions: 39
  - Everyone in key path cooperative: 1 sig: 64 WU
  - Up to 2 non-cooperative:         1 sig, 1 pk, 7 deep: 320 WU
  - More than 2 non-cooperative:     15 sig, 20 pk, 1 deep: 1632 WU
  - In Comparison, fully merkleized multisig (11628 parallel sessions): 1 sig, 1 pk, 14 deep: 544 WU
- 15-of-20 with up to 3 signers non-cooperative
  - Parallel signing sessions: 248
  - Everyone in key path cooperative: 1 sig: 64 WU
  - Up to 3 non-cooperative:         1 sig, 1 pk, 9 deep: 384 WU
  - More than 3 non-cooperative:     15 sig, 20 pk, 1 deep: 1632 WU
  - In Comparison, fully merkleized multisig (11628 parallel sessions): 1 sig, 1 pk, 14 deep: 544 WU
