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
Assume Alice has permanent pubkey `A = a*G` and ephemeral pubkey `A'`, Bob has
two pubkeys `B1 = b1*G` and `B2 = b2*G` and `H` is a cryptographic hash
function. The partially blind atomic swap protocol where Alice acts as a
tumbler and proceeds as follows.

1. Setup

   * Bob anonymously asks Alice to put coins into a key aggregated output O1
     with public key `P1 = H(A,B1,A)*A + H(A,B1,B1)*B1` (following "Simpler
     Schnorr Multi-Signatures with Applications to Bitcoin" by Pieter Wuille,
     Greg Maxwell and Andrew Poelstra).
   * Bob puts coins into a key aggregated output O2 with `P2 = H(A',B2,A')*A' +
     H(A',B2,B2)*B2`. As usual, before sending coins Alice and Bob agree on
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
        * the challenge `c'` for `A` as part of `P1`: `c' = c1*H(A,B1,A)`
        * the blinded challenge `c = c'+beta`
        * and the blinded signature of A times `G`: `T = R + c*A`
   * Bob sends `c` to Alice
   * Alice replies with an adaptor signature over `tx_A` spending `O2` with
     auxiliary point `T = t*G, t = ka + c*a` where `a` is the discrete
     logarithm of A.
3. Swap

    * Bob gives Alice his contribution to the signature over `tx_A`.
    * Alice adds Bob's contribution to her own signature and uses it to take
      her coins out of O2.
    * Due to previously receiving an adaptor signature Bob learns `t` from step (2).
4. Unblinding

   * Bob unblinds Alice's blind signature `t` as `t' = t+alpha` resulting in a
     regular signature `(R', t')` of Alice over `tx_B`.
   * Bob adds his contribution to `t'` completing `(R', s), s = t' + kb +
     c1*H(A,B1,A)*b1)` which is a valid signature over `tx_B` spending O1:
     ```
     s*G = (ka + (c'+beta)*a + alpha + kb + c1*H(A,B1,B1)*b1)*G
         = R + beta*A + alpha*G + c1*(H(A,B1,A)*a+*H(A,B1,B1)*b1)*G
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

Note that Bob can get a signature of A over anything including arbitrary
messages. Therefore, the Blockchain this is used in must not allow spending
more than one output with a single signature. The [SIGHASH_SINGLE
bug](https://underhandedcrypto.com/2016/08/17/the-2016-backdoored-cryptocurrency-contest-winner/)
for example would have been disastrous for this scheme.

Dealing with Aggregated Signatures
---
The above scheme is broken by aggregated signatures, because they allow spending
multiple inputs with a single signature. If Bob creates many funding txs with
Alice, he can create a tx spending all of them, and prepares a message for Alice
to sign which is her part of the aggregate signature of all the inputs. Alice
just dumbly signs any blinded message, so can't decide if it's an aggregated
sig or not. For example Bob may send Alice a challenge for an aggregate
signature covering output 1 with pubkeys `L1 = {A, B1}` and output 2 with
pubkeys `L2 = {A, B2}` as `c'=H(P1, 0, R', tx_B)*H(L1,A) + H(P2, 1, R',
tx_B)*H(L2,A)`.

A simple solution would be for Alice to create different pubkeys for every swap
instead of permanent pubkey `A`. Then in step 2 Alice sends one nonce (`Ra`) per
pubkey to Bob. Bob computes auxiliary points `T` for each of them, including the
one corresponding to A's pubkey he's really interested in - and requires an
adapter signature for each `T`.
* Note that simply sending multiple adaptor sigs is problematic. Say Alice
  sends one adaptor sig with auxiliary point `T1=t1*G` and one with aux
  point `T2=t2*G`. Then even without seeing the actual signature, by just
  subtracting the signatures Bob learns `t1 - t2`. Instead, Alice uses
  auxiliary points `H(T1)*t1*G and H(T2)*t2*G` revealing `H(T1)t1 - H(T2)t2`
  which is usually meaningless.

The downsides of this approach are increased communication and that Bob doesn't
know the complete list of Alice's pubkeys, so Alice can only send half of the
sigs, for example, reducing the anonymity set by 50% with 50% success
probability. Moreover, Alice can send fake signatures (i.e. signatures not
belonging to a legitimitate multi party output) such that Bob can not detemine
his anonymity set.
