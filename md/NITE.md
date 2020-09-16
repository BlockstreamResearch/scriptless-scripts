Non-interactive Threshold Escrow (NITE)
---

Threshold Schnorr signatures are [complicated](https://www.youtube.com/watch?v=Wy5jpgmmqAg).
Although taproot allows creating threshold policies using the script tree, threshold signatures are very useful because they can be key-spent and are therefore cheaper and more fungible.
One of the main practical challenges of threshold Schnorr signatures is that they require multiple rounds of secure broadcast (for example [FROST](https://eprint.iacr.org/2020/852)).
Moreover, often you do not want to contact the parties unless there is a dispute.
One such scenario is escrow, where there are three parties, buyer, seller and the escrow.
They can set up a scriptless script 2-of-3 spending policy using threshold Schnorr signatures, but that requires communicating with the escrow at setup time.

This document discusses Non-interactive Threshold Escrow (NITE), which allows instantiating a subset of threshold spending policies without an interactive setup.
This subset consists of policies that have two types of participants: those who are involved in the setup and those who are not.
We call the latter *escrows* because they can not sign arbitrary messages but instead are only allowed to release a secret to the party they ruled in favor of.
By using _verifiable encryption_, buyer and seller are guaranteed that the policy is in place without having to contact the escrows first.

This secret release mechanism is the reason why NITE is not as expressive as regular threshold signatures, because the escrows can only pick among a couple of fixed settlement transactions and are not able to sign a new transaction with one of the other parties.
On the other hand this allows using NITE to non-interactively set up Lightning Network payments which are conditional on the approval of a threshold (this also requires [multi-hop locks](multi-hop-locks.md)).

The general idea for the escrow setup in Lightning was described by ZmnSCPxj on the [lightning-dev mailing list](https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-June/002028.html).
This document answers the question of "whether it's possible to make such a proof" and generalizes from a single escrow to a multiple escrows.

Escrow Protocol with Adaptor Signatures
---
Let's have a look at the following example.
Assume Alice and Bob want to create an output with a scriptless 2-of-3 policy that includes an escrow.
Depending on some condition `c`, either Alice or Bob are allowed to spend the output.
If they disagree, the escrow will decide whether Alice or Bob gets the coin.

1. An unsigned funding transaction is created, sending coins to a 2-of-2 MuSig output between Alice and Bob.
2. Alice draws a scalar `t_A` uniformly at random, sends Bob an adaptor signature with adaptor `t_A*G` of a transaction sending the funding output to Bob. Alice also sends Bob a ciphertext which contains `t_A` encrypted to the escrows public key `E` pay-to-contract-tweaked as `E_c = E + hash(E, c)G`.
3. Bob does step 2 vice versa with adaptor secret `t_B`.
4. Both Alice and Bob send the ciphertext and the contract `c` to the escrow and ask if it decrypts to the DLog of `T_A = t_A*G` and `T_B = t_B*G` respectively.
5. If so, the funding tx is signed and broadcasted.

Now if there's no dispute they can spend their 2-of-2 output however they want.
If they can't agree on an outcome, either party can contact the escrow and ask for the adaptor secret, which would allow either of them to complete the adaptor signature and broadcast the settlement transaction.

Non-interactive Setup
---

The problem with above protocol is step 4.
Not only does it require interaction with the escrow even if there's no dispute, but it also requires revealing the contract (It may be possible to avoid the latter issue but note that the protocol must ensure that the escrow is not tricked into decrypting under anything but Alice and Bob's shared contract conditions).
In order to get rid of step 4, Alice and Bob use *verifiable encryption*, i.e., they create a non-interactive zero-knowledge proof to convince the other party that the ciphertext really is their adaptor secret encrypted to the tweaked escrow key.
Only if there is a dispute, Alice or Bob send their received ciphertext and the contract `c` to the escrow, who derives `E_c`, decrypts and returns the adaptor secret under the contracts conditions.

Verifiable Encryption
---
The [classic scheme](https://link.springer.com/content/pdf/10.1007/978-3-540-45146-4_8.pdf) for verifiable encryption of discrete logarithms can not be applied to secp256k1 adaptors because it only allows verification of specially constructed groups.
As of 2020-09 there are two promising ways to verifiably encrypt secp256k1 discrete logarithms: Purify and Juggling.

[Purify](https://eprint.iacr.org/2020/1057) was originally invented to create a MuSig protocol with deterministic nonces (DN).
This requires each signer to prove in zero knowledge that its own nonce contribution is the result of correctly applying a pseudo-random function (PRF) to the public keys and the message.
The Purify PRF can be efficiently implemented in an arithmetic circuit for the [Bulletproof](https://eprint.iacr.org/2017/1066.pdf) zero knowledge protocol.
As shown in the ["Further Applications"](https://eprint.iacr.org/2020/1057) section, the same techniques can be used to create a verifiable encryption scheme for discrete logarithms on secp256k1.
There are [python scripts](https://github.com/sipa/purify) to generate Purify arithmetic circuits as well as an [experimental branch of libsecp256k1-zkp](https://github.com/jonasnick/secp256k1-zkp/tree/bulletproof-musig-dn-benches) that uses Bulletproofs to prove and verify these arithmetic circuits in zero-knowledge.

Roughly speaking, encryption with [Juggling](https://arxiv.org/pdf/2007.14423v1.pdf) works by first splitting up the discrete logarithm `x` into multiple segments `x_k` of length `l` such that `x = sum_k 2^(kl) x_k`, then ElGamal-encrypt `x_k * G` to `Y` as `{ D_k, E_k } = { x_k*G + r_k*Y, r_k*G }`.
For every segment the encryptor creates a rangeproof showing that `D_k` is a Pedersen commitment and that the value is smaller than `2^l`.
Then the encryptor runs a sigma protocol showing that `{ sum D_k, sum E_k }` is a correct encryption of `x*G`.
Decryption happens by ElGamal-decrypting every `x_k * G` from `{ D_k, E_k }` and then determining `x_k` (which is in `[0, 2^l)`) by brute force.
Juggling is [implemented](https://github.com/ZenGo-X/JugglingSwap) as part of JugglingSwap which allows cross-chain and cross-curve atomic swaps.

Juggling is conceptually simpler than executing a PRF inside a bulletproof as in Purify.
Other than that, there are minor differences in proof size, proving and verification time.


Threshold Escrow
---

It is straightforward to replace the single escrows in Alice and Bob's setup with multiple escrows.
For example, they can have a policy such as

```
(Alice AND Bob) or ((Alice or Bob) and (2 of escrow1, escrow2, escrow3))
```

We can write `(2 of escrow1, escrow2, escrow3))` in disjunctive normal form as `(escrow1 AND escrow2) OR (escrow2 AND escrow3) OR (escrow1 AND escrow3)`.
Now Alice generates three random scalars `l_1`, `l_2` and `l_3` and uses her adaptor secret `t_A` to compute `r_1 = t_A - l_1`, `r_2 = t_A - l_2`, `r_3 = t_A - l_3`.
Then she verifiably encrypts `l_1` and `l_3` to escrow1, `r_1` and `l_2` to escrow2, `r_2` and `r_3` to escrow3 and sends the ciphertexts along with `l_1*G, r_1*G, l_2*G, r_2*G, l_3*G, r_3*G` to Bob.
Bob checks that `l_i*G + r_i*G = t_A*G` and verifies that the ciphertexts really decrypt to `l_i` and `r_i`.
We can extend this method of sharing the adaptor secret to any monotone boolean function of escrows.

NITE can also be used for more active parties than just Alice and Bob.
For a policy like `(Alice AND Bob AND Carol) OR (Alice AND escrow) OR (Bob AND escrow) OR (Carol AND escrow)`, Alice, Bob and Carol would set up a funding transaction with a 3-of-3 MuSig output.
Then they would send one adaptor signature and the adaptor secret encrypted to the escrow to everyone else.

Non-binary outcomes
---

Above we considered the case where after setup Alice and Bob each have a single settlement transaction with an adaptor signature from the other party.
It's easy to extend this to more outcomes, but a limitation of NITE is that the number of possible outcomes must not be too big, because they must be determined and adaptor signatures exchanged before the dispute can happen.
This means for example that NITE can not be applied to every [Smart Contract Unchained](https://zmnscpxj.github.io/bitcoin/unchained.html).
