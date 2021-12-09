# MuSig2 Adaptor Signatures

## Motivation
Since [MuSig2](https://eprint.iacr.org/2020/1261) is very similar to its predecessor, it is straightforward to create adaptor signatures similar to MuSig1.
The version of adaptor signatures as used in the multi-hop locks (aka PTLCs) [writeup](https://github.com/ElementsProject/scriptless-scripts/blob/master/md/multi-hop-locks.md) is

```
s'G = RA + hash(P, R + T, m)P
```

where `s'` is a partial signature for aggregated pubkey `P` with partial nonce `RA`, aggregated nonce `R` and adaptor point `T`.

Note that this means that the adaptor point `T` must be determined before opening the commitments in MuSig1 (i.e. before round 2)
Otherwise, an attacker can apply Wagner's algorithm by grinding `T` similar to how the attacker [can grind `m`](https://medium.com/blockstream/insecure-shortcuts-in-musig) if it's not determined before the nonce exchange.
MuSig2 solves the latter problem by using two nonces per participant.
More specifically, let `RA1, RA2` be Alice's and `RB1, RB2` be Bob's nonces.
Then `b = hash(P, RA1 + RB1, RA2 + RB2, m)` and Alice's "effective nonce" becomes `RA = RA1 + b*RA2`.

## MuSig2 Adaptor Signatures
The main idea is to include the adaptor point `T` into the hash function used to compute `b`
Then the nonce exchange round is purely a preprocessing step that can happen before `T` is known
More precisely, `T` is added to `RA1 + RB1` before hashing.

We use the notation from [Generalized Bitcoin-Compatible Channels](https://eprint.iacr.org/2020/476) adjusted for multi-signature schemes and without loss of generality restricted to two parties.

```
keyAgg(A, B):
    # compute the MuSig coefficients muA and muB, the
    # aggregated key P = muA*A + muB*B and return the
    # tuple (muA, P).

setupSession():
    r1, r2 <-$ rand()
    R1 := r1*G, R2 := r2*G
    return (state := (r1, R1, r2, R2), R1, R2)

# Create pre-signature with signing key x and a state as output by setupSession().
# Takes other signer's public key B and other signer's nonces from setupSession()
# RB1, RB2 and message m and adaptor T.
preSign_{x,state}((B, RB1, RB2), m, T):
    # Similar to regular MuSig signing, the same state must never be
    # reused for different preSign calls
    (muA, P) := keyAgg(x*G, B)
    (rA1, RA1, rA2, RA2) := state
    R1 := RA1 + RB1, R2 := RB1 + RB2
    b := hash(P, T + R1, R2, m)
    R := R1 + b*R2
    rA := rA1 + b*rA2
    pre_s := rA + hash(P, R + T, m)*muA*x
    return pre_s

# Verify pre-signature pre_s for public key B, nonces RB1, RB2 and the
# signer's public key A, the signer's nonces RA1 and RA2, message m
# and adaptor T.
preVerify_{B,RB1,RB2}((A, RA1, RA2), m, T, pre_s):
    (muA, P) := keyAgg(A, B)
    R1 := RA1 + RB1, R2 := RB1 + RB2
    b := hash(P, T + R1, R2, m)
    R := R1 + b*R2
    RA := RA1 + b*RA2
    return pre_s*G ?= RA + hash(P, R + T, m)*muA*A

Adapt(pre_s, t):
    s := pre_s + t
    return s

Ext(s, pre_s):
    return s - pre_s
```

Note that another option would be to compute `b` by concatenating the adaptor `T` to the string that is hashed instead of adding it to the nonces: `b = hash(P, R1, R2, m, T)`
But this has the downside of revealing to every participant in the multisig that an adaptor signature protocol is being executed
For example, if there is a MuSig setup with three signers and only two of them are making use of adaptor signatures, then this option would require the third signer to know about the adaptor to compute `b`.

### Correctness
```
let
    # Alice sets up session
    (state, RA1, RA2) := setupSession()
    # Bob sets up session
    (_, RB1, RB2) := setupSession()
    # Alice may obtain RB1, RB2 before generating A
    (x, A) := KeyGen()
    (_, B) := KeyGen()
    # Alice creates a pre-signature for Bob
    pre_s := preSign_{x,state}((B, RB1, RB2), m, T)
    s := Adapt(pre_s, t)
    t' := Ext(s, pre_s)
    Verify_{B,RB1,RB2}((A, RA1, RA2), m, s):
        # MuSig2 partial sig verification. If passing, Bob can complete it to
        # a Schnorr signature.
        preVerify_{B,RB1,RB2}((A, RA1, RA2), m, 0, s):

then
    preVerify_{B,RB1,RB2}((A, RA1, RA2), m, T, pre_s) = true
    Verify_{B,RB1,RB2}((A,RA1+T,RA2), m, s) = true
    t'*G = T
```

## Security

What follows are security definition and proof sketches for adaptor signatures following [Generalized Bitcoin-Compatible Channels](https://eprint.iacr.org/2020/476)
They are not too different to the proof for Schnorr adaptor signatures in that publication, but does not require strong unforgeability of the underlying signature scheme
The sketches are intended to test above definition of the scheme, give some intuition about what adaptor signatures tries to achieve and should give a bit more confidence as long as there exists no complete proof.

### aExistential Unforgeability under Chosen Message Attack

Loosely speaking, this means that an forger F shouldn't be able to forge a signature even after obtaining a pre-signature
This is formalized with the following game:

```
Q := empty
(x, A) := KeyGen()
(state, RA1, RA2) := setupSession()

(B, RB1, RB2, m) <- F(O_S, O_pS, A, RA1, RA2)
t <-$ rand(), T := t*G
pre_s := preSign_{x,state}((B, RB1, RB2), m, T)
(RA1', RA2', s') <- F(O_S, O_pS, pre_s, T)
return m notin Q
       and Verify_{B,RB1,RB2}((A, RA1', RA2'), m, s)
```

where `F(O_S, O_pS, ...)` means running the forger with access to signing oracle `O_S` and `O_pS` and additional inputs
`O_S` consists of two sub-oracles
The first runs `setupSession()` and returns `R1` and `R2` to the caller and the second accepts an arbitrary nonces, public key and message and returns partial signature for the session that passes `Verify`
Likewise, `O_pS` consists of a session-setup sub-oracle and a sub-oracle that returns a pre-signature for arbitrary nonces, public key, message and adaptor that passes `preVerify`
Both `O_S` and `O_pS` insert `m` in `Q`.

Thus, the game starts by running the forger with the public key and generated public nonces until it provides a public key, nonces and message
The game responds with a pre-signature on the message with a fresh adaptor and the forger wins if it produces a signature for a message that hasn't appeared in a (pre-)signature query.

We will now describe an algorithm that transforms a winner of the aEUF-CMA into a winner against a EUF-CMA for multisignatures (as defined in the MuSig2 paper) which is simplified for brevity
This variant is restricted to two, and considers forgeries of _partial_ signatures, i.e
signatures that pass `Verify` as defined above
First we note that queries to the signing oracle `O_S` can be directly relayed to the EUF-CMA game (or so it seems, see below)
In order to answer queries to the pre-signing oracle `O_pS` with nonces `(RB1, RB2)` we query the EUF-CMA signing oracle with `(RB1 + T, RB2)`.

Instead of running `KeyGen()` and `setupSession()` we obtain `A`, `RA1` and `RA2` from the MuSig2 EUF-CMA game.
To produce a pre-signature on the forger's chosen message, we proceed in the same way as with answering `O_pS` queries.
Crucially, if the forger succeeds in producing a signature, this does not constitute a forgery in the EUF-CMA game, because we've just used its signing oracle on the same message `m`.
Therefore, we distinguish two cases:

1. `s' = Adapt(pre_s, t)`
    The attacker would have broken the hardness of the discrete logarithm of `T` which we assume to be hard.
2. `s' != Adapt(pre_s, t)`.
    Then we have
    ```
    let
        s := Adapt(pre_s, t)
        RA := RA1 + b*RA2
        RA' := RA1' + b'*RA2'
        (muA, P) := keyAgg(A, B)

    s*G != pre_s*G
    <=>
    RA + T + hash(P, R, m)*muA*A != RA' + hash(P, R', m)*muA*A
    <=>
    RA + T != RA' or R != R'
    <=>
    R != R' (since absent collisions, RA + T != RA' => R != R')
    ```
    We can use this fact in order to program the random oracle of the forger to ensure that from the point of view of the EUF-CMA game, `s'` is a forgery not on `m`, but on some `m' != m`
    Let's call the random oracle provided by the EUF-CMA game `hash^G` and define the random oracle provided to the forger for signature hash queries:
    ```
    hash^F(P, R, m):
        if T[R, m] undefined:
            m' <-$ rand()
            M[R, m] := m'
            T[R, m] := hash^G(P, R, m')
        return T[R, m]
    ```
    where `M` and `T` are tables that are initialized empty
    Thus, instead of relaying `O_S` and `O_pS` queries directly, we compute the combined `R`, query `hash^F(P, R, m)` to make sure that `m' = M[R,m]` is defined and pass the query to the EUF-CMA game after replacing `m` with `m'`.
    Similarly, in order to produce a pre-signature on the forgery message `m`, we replace it with `M[R,m]`.
    Then we have
    ```
    s*G = RA + hash^F(P, R, m)A = RA + hash^G(P, R, M[P,R])*muA*A
    and
    pre_s*G = RA' + hash^F(P, R', m)A = RA + hash^G(P, R', M[P,R'])*muA*A
    ```
    Since `R != R'` we have with overwhelming probability that `M[P,R] != M[P,R']` and therefore `s'` counts as a forgery in the EUF-CMA game.

### Pre-signature adaptability

This property captures that any pre-signature passing `preVerify` with adaptor `T = t*G` passes `Verify` after adapting with `t`
In the case of MuSig2 adaptors this can be easily checked by applying the definitions of `preVerify`, `Adapt` and `Verify`.

### Witness extractability

This property holds if one can always extract a witness from a pre-signature and a signature passing `Verify`
This is formalized as a game similar to the aEUF-CMA game, but here the forger returns also the adaptor `T` in its first execution
The game creates a pre-signature `pre_s` and the forger wins if it produces a forgery `s'` and `Ext(s', pre_s)` does not return the adaptor secret `T`.

```
Q := empty
(x, A) := KeyGen()
(state, RA1, RA2) := setupSession()

(B, RB1, RB2, m, T) <- F(O_S, O_pS, A, RA1, RA2)
pre_s := preSign_{x,state}((B, RB1, RB2), m, T)
(RA1', RA2', s') <- F(O_S, O_pS, pre_s)
t' := Ext(s', pre_s)
return m notin Q
       and t'*G != T
       and Verify_{B,RB1,RB2}((A, RA1', RA2'), m, s')
```

The proof is almost identical to the proof or aEUF-CMA under the EUF-CMA of MuSig2 partial signatures.
Again, we distinguish between `hash^G` and `hash^G` and relay signing and pre-signing queries to `O_S` and `O_pS` accordingly.
Instead of generating the key and session state, we request `RA1` and `RA2` from the EUF-CMA signing oracle and run the forger.
To pre-sign the forger's chosen message, we compute the sessions combined `R` and query the EUF-CMA signing oracle with `RB1 + T, RB2, M[R,m]`.
Since `Ext(s', pre_s)*G != T` we have

```
let
    RA := RA1 + b*RA2
    RA' := RA1' + b'*RA2'
    (muA, P) := keyAgg(A, B)

pre_s*G + T != s'*G
<=>
RA + T + hash(P, R, m)A != RA' + hash(P, R', m)A
<=>
RA + T != RA' or R != R'
<=>
R != R'
```

Thus, `M[R,m] != M[R',m]` with overwhelming probability which means that from the point of view of the EUF-CMA game, the message in the signing query for `pre_s` is different to the forgery message and results in a win against the game.
