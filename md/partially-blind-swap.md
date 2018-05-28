Partially Blind Atomic Swap Using Adaptor Signatures
===========================

In this scheme one of the participants of the swap does not learn which coins
are being swapped. For example if Alice engages in a partially blind atomic
swap with Bob and Carol, she would not be able to determine if a swapped output
belongs to Bob or Carol (assuming the transaction amounts are identical or
confidential). This property is very similar to
[TumbleBit](https://eprint.iacr.org/2016/575.pdf) but in the form of a
[scriptless
script](https://github.com/apoelstra/scriptless-scripts/blob/master/md/atomic-swap.md)
and therefore purely in the elliptic curve discrete logarithm setting.

The basic idea is that the discrete logarithm of the auxiliary point `T` in the
adaptor signature is not chosen uniformly at random by Alice. Instead, Bob
computes `T = t*G` where `t` is a [blind Schnorr
signature](https://blog.cryptographyengineering.com/a-note-on-blind-signature-schemes/)
of Alice over a transaction spending the funding transaction without knowing `t`
(similar to [Discreet Log Contracts](https://adiabat.github.io/dlc.pdf)).

Protocol description
---
Assume Alice has a permanent public key `A = a*G`, ephemeral pubkey `A1 = A +
h*G` and ephemeral pubkey `A2`, Bob has two pubkeys `B1 = b1*G` and `B2 = b2*G`
and `H` is a cryptographic hash function. Public key aggregation in "2-of-2"
scripts is achieved with [MuSig](https://eprint.iacr.org/2018/068.pdf) and the
signature scheme is adapted from
[Bellare-Neven](https://cseweb.ucsd.edu/~mihir/papers/multisignatures-ccs.pdf).
The partially blind atomic swap protocol where Alice acts as a tumbler works as
follows.

1. Setup

   * Bob anonymously asks Alice to put coins into a key aggregated output O1
     with public key `P1 = H(A1,B1,A1)*A1 + H(A1,B1,B1)*B1`.
   * Bob puts coins into a key aggregated output O2 with `P2 = H(A2,B2,A2)*A2 +
     H(A2,B2,B2)*B2`. As usual, before sending coins Alice and Bob agree on
     timelocked refund transactions in case one party disappears.
2. Blind signing

   Bob creates a transaction `tx_B` spending O1. Then Bob creates an auxiliary
   point `T = t*G` where `t` is a Schnorr signature over `tx_B` in the
   following way:

    * Bob asks Alice for nonce `Ra = ka*G`
    * Bob creates nonce `Rb = kb*G`
    * Bob computes
        * the combined nonce `R = Ra+Rb`
        * the "blinded" nonce `alpha,beta = rand, R' = R + alpha*G + beta*A`
        * the challenge `c1` as the Bellare-Neven style challenge hash of
          `tx_B` with respect to `P1` and input 0 for aggregated key `P1`: `c1
          = H(P1, 0, R', tx_B)`
        * the challenge `c'` for `A1` as part of `P1`: `c' = c1*H(A1,B1,A1)`
        * the blinded challenge `c = c'+beta`
        * and the blinded signature of A times `G`: `T = R + c*A`
   * Bob sends `c` to Alice
   * Alice replies with an adaptor signature over `tx_A` spending `O2` with
     auxiliary point `T = t*G, t = ka + c*a` where `a` is the discrete
     logarithm of permanent key `A`.
3. Swap

    * Bob gives Alice his contribution to the signature over `tx_A`.
    * Alice adds Bob's contribution to her own signature and uses it to take
      her coins out of O2.
    * Due to previously receiving an adaptor signature Bob learns `t` from step (2).
4. Unblinding

   * Bob unblinds Alice's blind signature `t` as `t' = t + alpha + c'*h` where
     c' is the unblinded challenge `h` is the tweak for `A1`. This results in a
     regular signature `(R', t')` of Alice (`A1`) over `tx_B`.
   * Bob adds his contribution to `t'` completing `(R', s), s = t' + kb +
     c1*H(A1,B1,B1)*b1` which is a valid signature over `tx_B` spending O1:
     ```
     s*G = t' + kb + c1*H(A1,B1,B1) * b1
         = (ka + (c'+beta)*a + alpha + c'*h + kb + c1*H(A1,B1,B1) * b1)*G
         = R + beta*A + alpha*G + c1*(H(A1,B1,A1) * (a+h) + H(A1,B1,B1) * b1)*G
         = R' + H(P1, 0, R', tx_B)*P1
     ```
   * Bob waits to increase his anonymity set and then publishes the signature
     to take his coins from O1 resulting in the following transaction graph:
     ```
     +------------+  (R', s)   +------------+
     |         O1 +----------->|         ...|
     +------------+            +------------+
     Alice's setup tx          tx_B

     +------------+            +------------+
     |         O2 +----------->|         ...|
     +------------+            +------------+
     Bob's setup tx            tx_A
     ```

As a result, Alice can not link Bob's original coins and his new coins. From
Alice's perspective `tx_B` could have been just as well the result of a swap
with someone else.

Blind Schnorr signatures suffer from a vulnerability known as "parallel attack"
([Security of Blind Discrete Log Signatures Against Interactive Attacks, C. P.
Schnorr](http://www.math.uni-frankfurt.de/~dmst/research/papers/schnorr.blind_sigs_attack.2001.pdf))
where the attacker collects a bunch of nonces `R` and sends specially crafted
challenges `c`. The responses can be combined to create a signature forgery.
Among proposed countermeasures is a simple, but currently unproven trick by
Andrew Poelstra in which the signer randomly aborts after receiving a
challenge.


A simpler scheme that would be broken by Aggregated Signatures
---
Note that Bob can get a signature of A over anything including arbitrary
messages. Therefore, Alice must only use fresh ephemeral keys `A1` when
creating outputs. This complicates the protocol because at the same time Alice
must not be able to determine for which exact input she signs. As a result,
It's Bob's job to apply tweak `h` to convert a signature of `A` to `A1`.

A simpler protocol where Alice uses `A` instead of `A1` is broken by aggregated
signatures because it allows spending multiple inputs with a single signature.
If Bob creates many funding txs with Alice, he can create a tx spending all of
them, and prepares a message for Alice to sign which is her part of the
aggregate signature of all the inputs. Alice just dumbly signs any blinded
message, so can't decide if it's an aggregated sig or not. For example Bob may
send Alice a challenge for an aggregate signature covering output 1 with
pubkeys `L1 = {A, B1}` and output 2 with pubkeys `L2 = {A, B2}` as `c'=H(P1, 0,
R', tx_B)*H(L1,A) + H(P2, 1, R', tx_B)*H(L2,A)`.

Similarly, the [SIGHASH_SINGLE
bug](https://underhandedcrypto.com/2016/08/17/the-2016-backdoored-cryptocurrency-contest-winner/)
for example would have been disastrous for this scheme. In general, the
Blockchain this is used in must not allow spending more than one output with a
single signature.
