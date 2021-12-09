Multi-Hop Locks from Scriptless Scripts
===========================

Multi-hop locks are protocols that allow two parties to exchange coins and proof of payment without requiring a mutual funding multisig output.
Instead, they are connected by hopping through intermediate nodes who are connected by having a shared funding multisig output.
Multi-hop locks based on cryptographic hashes instead of scriptless scripts are used in the [Lightning Network protocol](https://github.com/lightningnetwork/lightning-rfc) to route payments.

Scriptless script multi-hop locks were introduced in a [post to the mimblewimble mailing list](https://lists.launchpad.net/mimblewimble/msg00086.html) and formally defined in the paper [Privacy-preserving Multi-hop Locks for Blockchain Scalability and Interoperability](https://eprint.iacr.org/2018/472.pdf).
By using scriptless scripts they result in smaller transactions which look like regular transactions and therefore improve privacy.
More importantly, they allow [payment decorrelation](https://medium.com/@rusty_lightning/decorrelation-of-lightning-payments-7b6579db96b0) which means that nodes in a multi-hop lock can not determine (absent timing and coin amount analysis) if they are on the same path, i.e. they don't know if they are forwarding the same payment.
Correlation attacks are especially problematic if the first and last intermediate nodes are colluding because they would learn source and destination of a payment.
In addition, scriptless script multi-hop locks enable improved proof of payment and atomic multi path payments (see below).

Notation
---

- `Pij` is the MuSig2 aggregated public key of users `i` and `j`. See the [MuSig2 paper](https://eprint.iacr.org/2020/1261) for more details.
- `T := t*G` for a randomly chosen `t` is called the adaptor with adaptor secret `t`.
- `psig(i,m,T)` is a pre-signature from signer `i` for `m` and adaptor `T`.
- `sig(i,m) := psig(i,m,T) + t` is the complete Schnorr signature from user `i`.

Protocol
---

![multi-hop-locks](images/multi-hop-locks.png)

In the setup phase the recipient chooses `z` at random and sends the sender `z*G`.
The sender will set up the multi-hop locks such that a successful payment reveals `z` to her and only her.
Knowledge of `z` can be a proof of payment which is similar in concept to payment preimages in Lightning (see section below for details).

We picture the payment starting from the sender on the left side through intermediate nodes to the recipient on the right side.
The setup phase continues with the sender setting up a tuple `(Li,yi,Ri)` consisting of the *left lock* `Li` and *right lock* `Ri` for every node `i` in the following way:

- Every `yi` is a scalar uniformly chosen at random.
- The sender's own left lock `L0` is set to `z*G` which was previously received from the recipient.
- For every lock `Ri` for node `0<=i<n` and `Lj` for node `j=i+1` the sender sets `Ri <- Li + yi*G` and `Lj <- Ri` (see the diagram).

Note that in Lightning, the sender would not directly send `(Li,yi,Ri)` to the intermediate nodes: it will instead use the payment onion to carry those values without disclosing his identity to intermediate nodes.

In the update phase adjacent nodes add a multisig output to their off-chain transactions similar to how they would add an HTLC output in Lightning.
We will call this new type of scriptless script output *Point Time Locked Contract* (PTLC).
Just like HTLCs, PTLCs have a time out condition such that the left node can reclaim her coins if the payment fails.
But otherwise PTLCs are plain 2-of-2 MuSig2 outputs and the hashlock is only implicitly added to the output when a partial signature is received (see below).
For demonstration purposes we assume [eltoo](https://blockstream.com/eltoo.pdf)-style channels which means that both parties have symmetric state and there's no need for revocation.

If the payment does not time out, the coins in the scriptless script PTLC output shared by two adjacent nodes will be spent by the right node.
Therefore, the left node `i` creates a transaction `txj` that spends the PTLC and sends the coins to an output that the right node `j` controls.
It is assumed that the nonce exchange round required by the MuSig2 protocol happened earlier when it was more convenient for both nodes (e.g. when establishing a connection) such that this communication round is not on the critical path of the payment.

Upon receiving notice of the new PTLC, the right node `j` creates transaction `txj` and partial signature `psig(j,txj,Lj)` over `txj`.
The left node verifies the partial signature and sends its own partial signature for `txj` to the right node in the following two cases:

- the left node is the sender
- the left node `i` received a signature `psig(i-1,txi,T-yi*G)` from the preceding node `i-1` for the left node's transaction `txi`. In combination with the partial signature just received from the right node, it is guaranteed that as soon as the right node spends the coins, the left node can open its left lock and spend the coins with `txi` as we will see below.

Therefore, the update phase starts with the leftmost pair and continues to the right.
After receiving the partial signature from the left, the right node can complete it as soon as it learns the secret of its left lock.
In order to reduce the overall number of communication rounds the setup phase and update phase can be merged together (e.g. using the payment onion in Lightning).

The settlement phase begins when the recipient receives the partial signature from its left node.
The multi-hop locks were set up by the sender such that the receiver can add her secret to the left node's partial signature and sum the result with her own partial signature.
The result is a final signature for the right node's (the recipient's) transaction.
At this point the right node can broadcast the transaction to settle on-chain (in case the left node disappears or tries to cheat).

In this case the left node notices the transaction signature and learns its right lock secret by subtracting the right node's previously received partial signature and its own partial signature:

```text
sig(tx,T) - psig(i,tx,Ri) - psig(j,tx,Lj) = yj
```

Alternatively, the right node can send its secret `yj` directly to the left node and request to update commitment (LN-penalty) or settlement (eltoo) transaction such that the PTLC is removed, the left node's output amount is decreased by the payment amount and the right node's output amount is increased by that amount.
If the left node would not follow up with an update, the right node can still broadcast the transaction before the PTLC times out.

Either way, once the recipient claims the payment, the left node learns the right lock secret, computes its left lock secret by subtracting `yi` and uses it to create the final Schnorr signature over her transaction.
This happens on every node until up to the sender, who learns the proof of payment `z` which completes the payment.

Proof of Payment (PoP)
---

The main difference to HTLCs is that the proof of payment (`z`) is only obtained by the sender and not by every node along the route.
Therefore, the proof of payment can be used to authenticate the sender to the recipient.
It is not necessary to reveal the PoP itself but instead a signature of `z*G` can be provided.
Due to payment decorrelation intermediate nodes can not associate a payment with the PoP.

Obviously, not only the sender is able prove knowledge of `z`.
Everyone the recipient or sender choose to share `z` with can do so too which makes it unclear who actually paid.
Therefore a signed statement (invoice) from recipient should be sent to sender that includes `z*G` and the sender's public key.
Then the PoP is both a signature with the PoP and the sender's secret key which can only be provided by the sender (or everyone the sender chooses to collaborate with).

Ideally a single static invoice would be payable by multiple parties allowing spontaneous payments without requiring extra communication with the recipient.
But this is not compatible with PoPs because the PoP must be created from fresh randomness for every payment.
However, recurring payments from a single sender [can be done using hash chains](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-November/001496.html).

Atomic Multipath Payments (AMP)
---

With scriptless script multi-hop locks it is possible to make multi-path payments similar to [*base MPP*](https://github.com/lightningnetwork/lightning-rfc/pull/643) while allowing payment decorrelation between the paths.
The sender sets up multiple routes to the recipient using uncorrelated locks such that any partial payment claimed by the recipient reveals the proof of payment (`z`) to the sender.
Because the recipient doesn't want to give up the PoP for just a partial payment, she waits until all routes to her are fully established and claims all the partial payments at once.

In the original [original base AMP proposal](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-February/000993.html) proposal *atomicity* is achieved not only by incentive, but also by setting up the the paths such that the recipient's secret (`z`) is only revealed once all paths are established.
However, in this proposal the payer is not able to obtain a proof of payment.
With multi-hop locks we can both have the atomicity of original base AMP and the proof of payment.
This is referred to as [*high AMP*](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-November/001494.html).

In high AMP the sender first draws a random number `q` and determines random `q1, ... qn` where `n` is the number of paths such that `q = q1 + ... qn`.
The sender adds `q*G` to the recipient's payment point on every path, who is therefore unable to claim any payment because the recipient is not aware of `q`.
However, when setting up each path `i` the sender sends `qi` along to the recipient.
As soon as all paths are established, the recipient can compute `q` and claim the payments.

Cancellable payments
---

In the current version of Lightning, payments may be stuck for a very long time if an intermediate node goes offline while it was forwarding the payment.
The payer cannot safely retry, because if the intermediate node goes back online before the PTLC times out, the payer may pay twice.

Example scenario:

1. Alice sends a 10mBTC PTLC to Bob, who should forward to Dave (Alice -> Bob -> Dave).
2. Bob receives the PTLC but does not forward anything to Dave.
3. After a few blocks, Alice gets impatient and retries the payment via Carol instead of Bob (Alice -> Carol -> Dave).
4. This payment succeeds: Alice has correctly paid 10mBTC to Dave and receives a proof-of-payment.
5. However, Bob wakes up before his PTLC-timeout and forwards the first 10mBTC to Dave.
6. It's free money for Dave, so Dave accepts it and the PTLC correctly fulfills.
7. Alice has received her proof-of-payment, but she paid 20mBTC instead of 10mBTC.

This can be avoided if the payment needs a secret from the sender to be fulfilled.
This solution was originally introduced as [stuckless payments](https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-June/002029.html).

The sender secret is `y0+y1+y2`. Alice MUST NOT send it to Dave during the setup phase.
Alice does send `(z+y0+y1+y2)*G` to Dave as his left lock, which lets Dave discover `(y0+y1+y2)*G`.
At the end of the update phase, Dave cannot create the signature because he is missing `y0+y1+y2`.
Dave can request `y0+y1+y2` from Alice (and present `(y0+y1+y2)*G` to prove that he received the PTLC).
When Alice receives that request, she knows that the PTLC was correctly forwarded all the way to Dave.
She can now safely send `y0+y1+y2` to Dave which allows the settlement phase to begin.

In case Dave does not reply and the payment seems to be stuck, Alice can now retry with another secret `y0'+y1'+y2'` (and potentially another route).
If this one succeeds, she simply needs to never reveal `y0+y1+y2` and the stuck payment can never be fulfilled.
Thanks to that mechanism, Alice can safely retry stuck payments without the risk of being double-spent.

Note that this doesn't prevent the payment from being stuck during the settlement phase (if a node goes offline).
However intermediate nodes have a much bigger incentive to be online and forward during the settlement phase:

- During the update phase they're receiving bitcoins from their left peer: they haven't sent anything yet so their only incentive to forward is the fee they will collect.
- During the settlement phase they have sent bitcoins to their right peer: they now have an incentive to forward to the left peer to collect the incoming payment.

Resources
---

* [MuSig2](https://eprint.iacr.org/2020/1261)
* [Lightning Network protocol](https://github.com/lightningnetwork/lightning-rfc)
* [Scripless Scripts in Lightning](https://lists.launchpad.net/mimblewimble/msg00086.html)
* [Privacy-preserving Multi-hop Locks for Blockchain Scalability and Interoperability](https://eprint.iacr.org/2018/472.pdf)
* [Payment Decorrelation](https://medium.com/@rusty_lightning/decorrelation-of-lightning-payments-7b6579db96b0)
* [eltoo](https://blockstream.com/eltoo.pdf)
* [Post-Schnorr Lightning Txs](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-February/001038.html)
* [Bolt11 in the world of Scriptless Scripts](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-November/001496.html)
* [Base AMP](https://lists.linuxfoundation.org/pipermail/lightning-dev/2018-November/001577.html)
* [Stuckless Payments](https://lists.linuxfoundation.org/pipermail/lightning-dev/2019-June/002029.html)
