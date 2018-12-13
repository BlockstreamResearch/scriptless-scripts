Atomic Pedersen Swap Using Adaptor Signatures
===

An atomic Pedersen swap exchanges a coin with the opening `(r, x)` of a
Pedersen commitment `r*G + x*H`. By using adaptor signatures this can be done
as a scriptless script such that a Bitcoin output that requires revealing an
opening appears like a normal payment on-chain. Therefore, it can be a
replacement for scripts involving `OP_SHA256 <hash> OP_EQUAL` when it's not
required to commit or open publicly.

Additionally, it allows using Pedersen commitments in Bitcoin or any other
crypto-currency supporting adaptor signatures without adding Pedersen
commitment in the consensus code (for example in the form of a new opcode).
Pedersen commitments are *homomorphic commitments* which enables many
interesting applications. For example, proving knowledge of the opening of a
commitment in zero knowledge or re-blinding a given commitment by adding `r'*G`
(maybe useful in lightning). Current applications of Pedersen commitments in
crypto-currencies include Confidential Transactions, Confidential Assets and
Mimblewimble.

One important ingredient for these swaps is a multiplication proof of Pedersen
commitments described below.


Multiplication Proof for Pedersen Commitments
---
This is a non-interactive zero knowledge proof that for given Pedersen
commitments `Q = r*G + x*H`, `T1 = t1*G` and `T2 = t2*G` it holds that `r =
t1*t2`. The given construction is special case (commitment to 0) of the proof
from the paper [Zero-knowledge proofs of knowledge for group
homomorphisms](https://sci-hub.la/10.1007/s10623-015-0103-5) by Ueli Maurer
section 6.7 with the addition of the Fiat-Shamir heuristic.

Informally, the scheme consists of the two algorithms "generate" and "check":

* Generate
  ```
  select `k1, k2` to be uniformly random scalars and compute
  R1 <- k1*G
  R2 <- k1*t2*G + k2*H
  s1 <- k1 + H(R1, R2)*t1
  s2 <- k2 + H(R1, R2)*x
  return proof (R1, R2, s1, s2)
  ```

* Check proof `(R1, R2, s1, s2)`
  ```
  s1*G ?= R1 + H(R1, R2)*T1
  s1*T2 + s2*H ?= R2 + H(R1, R2)*Q
  ```

It helps to get some intuition for the proof by verifying completeness:
```
s1*G = k1*G + H(R1, R2)*t1*G
     = R1 + H(R1, R2)*T1
s1*T2 + s2*H = k1*T2 + H(R1,R2)*t1*T2 + k2*H + H(R1,R2)*x*H
             = k1*t2*G + k2*H + H(R1,R2)*(t1*T2 + x*H)
             = R2 + H(R1, R2)*Q
```


Protocol rationale
---
Assume someone wants to buy the opening `(r, x)` of a Pedersen commitment `Q =
r*G + x*H` from a seller. The seller can't just use `r*G` as the auxiliary
point in an adaptor signature and send it to the buyer. Upon receiving `r*G`
the buyer would compute `Q - r*G = x*H` and simply brute-force `x` without
paying. This is where the multiplication proof for Pedersen commitments comes
into play: the seller chooses t1 and t2 s.t. `t1*t2 = r`, sends `T1 = t1*G` and
`T2 = t2*G` as auxiliary points to the buyer along with the multiplication
proof. Obtaining `r` from `T1` and `T2` is the computational Diffie-Hellman
problem, but learning `t1` and `t2` during the swap allows the buyer to compute
`r`.

Because `x` is multiplied by `H` and not `G` there is no straightforward way to
similarly put `x*H` in an adaptor signature. Let `xi` be the `i`-th bit of `x`.
The seller creates one Pedersen commitment `Qi = ri*G + xi*G` for every bit of
`x`. After learning all `ri` during the swap, the buyer can reconstruct `x`
bitwise by checking whether `Qi` is a commitment to `0` or `1`. Committing to
each bit of a value in a Pedersen commitment in a verifiable way is exactly
what the range proof in [confidential
transactions](https://people.xiph.org/~greg/confidential_values.txt). So we
can abuse that scheme not to prove ranges, but to prove that each `Qi` commits
to a bit of `x`.

As a result, the seller must send an adaptor signatures for the factors `ti1`
and `ti2` of each `ri`. Simply sending multiple adaptor sigs is problematic.
Say the seller sends one adaptor sig with auxiliary point `Ti1=ti1*G` and one
with aux point `Ti2=ti2*G`. Then even without seeing the actual signature, by
just subtracting the signatures the buyer learns `ti1 - ti2`. Instead, the
seller uses auxiliary points `H(Ti1)*ti1*G and H(Ti2)*ti2*G` revealing
`H(Ti1)ti1 - H(Ti2)ti2` which is meaningless for the buyer.


Protocol description
---
Assume someone wants to buy the opening `(r, x)` of a Pedersen commitment `Q =
r*G + x*H` from a seller.

1. Setup

    * The seller publishes a range proof to allow potential buyers to later
      reconstruct `x` from just `Q` and `r`.A ssuming a prime order group with
      an order close to `2^256` the seller publishes `(Q0, ..., Q255, e, s0,
      ..., s255)` where `sum(Qi) = Q` and `e = hash(si*G + hash(si*G +
      e*Qi)*(Qi-2^i*H))`.
    * The buyer checks the range proof and sends the agreed-upon amount of
      coins to a key-aggregated multisig output of the buyer and seller (after
      receiving a timelocked refund transaction signed by the seller).
2. Adaptor signatures

    * Just as in regular atomic swaps using adaptor signatures, the parties
      agree on an `R` for the the signature. The seller creates a transaction
      spending the coins from the multisig output and computes a Bellare-Neven
      challenge `c` for the transaction.
    * For each bit commitment `Qi`, seller generates a uniformly random scalar
      `ti1` and sets `ti2`, such that `ti1*ti2*G = ri*G = Qi-xi*H`. Then the
      seller computes `Ti1 = ti1*G` and `Ti2 = ti2*G` and sends the following
      adaptor signatures `si1` and `si2` with auxiliary points `H(Ti1)*Ti1` and
      `H(Ti2)*Ti2` to Bob:
      ```
      si1 = k + H(Ti1)ti1 + c*a
      si2 = k + H(Ti2)ti2 + c*a
      ```
      along with a multiplication proof for Pedersen commitments proving the
      multiplicative relationship of the blinding factors of Ti1, Ti2 and Qi.
3. Swap

    * The buyer verifies the adaptor signatures and multiplication proofs and
      sends his contribution to the signature.
    * The seller completes the signature `(R, s)` and publishes it along with
      the transaction to take her coins.
    * Just as in regular atomic swaps using adaptor signatures, the buyer can
      recover the discrete logarithm of the auxiliary points by subtracting s
      from the corresponding adaptor signature. So for each bit commitment, the
      buyer is able to recover `ti1` and `ti2`.
    * Because it holds that `ti1*ti2 = ri`, the buyer can reconstruct `x` by
      setting the `i`-th bit of `x` to `0` if `Qi == ti1*ti2*G + 0*H` and to
      `1` otherwise.
