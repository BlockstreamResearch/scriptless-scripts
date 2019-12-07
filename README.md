# Scriptless Scripts
Scriptless scripts is an approach to designing cryptographic protocol on top of Bitcoin which avoids execution of explicit smart contracts.

* **[Adaptor Signatures and Atomic Swaps from Scriptless Scripts](md/atomic-swap.md)**
  * This document describes adaptor signatures and multisignatures, which are the original building blocks of scriptless scripts.
    It also describes an atomic swap protocol using these building blocks.
* **[Partially Blind Atomic Swap Using Adaptor Signatures](md/partially-blind-swap.md)**
  * In this scheme one of the participants of the swap does not learn which coins are being swapped.
* **[Atomic Pedersen Swap Using Adaptor Signatures](md/pedersen-swap.md)**
  * An atomic Pedersen swap exchanges a coin with the opening `(r, x)` of a Pedersen commitment `r*G + x*H`.
* **[Multi-Hop Locks from Scriptless Scripts](md/multi-hop-locks.md)**
  * Multi-hop locks are protocols that allow two parties to exchange coins and proof of payment without requiring a mutual funding multisig output (also known as "Lightning with Scriptless Scripts"). 
