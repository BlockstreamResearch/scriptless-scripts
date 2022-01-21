import math
from itertools import combinations as comb

def combinations(n, t):
    return [tuple(a) for a in comb(range(0, n), t)]

# Test whether the proposed spending paths Cp are actually sane
def test_paths(Cp, n, t, k):
    if k > n - t:
        return False
    # no duplicates
    if len(Cp) != len(set(Cp)):
        return False
    for c in Cp:
        if len(c) != t:
            return False
        if max(c) >= n:
            return False
    D = combinations(n, k)
    for d in D:
        not_in_common = 0
        for c in Cp:
          c_set = set(c)
          d_set = set(d)
          if not (c_set & d_set):
              not_in_common = 1
        if not_in_common == 0:
            return False
    return True

# Test test_paths
n = 5
t = 3
k = 1
assert(test_paths(combinations(n, t), n, t, k))
assert(not test_paths([(1,2,3)], n, t, k))
k = 2
assert(test_paths(combinations(n, t), n, t, k))
k = 1
# 2 have 2 common, 1 has only one common
assert(test_paths([(1,2,3), (0,2,3), (0,1,4)], n, t, k))
# doesn't work since 0 is always a required signer
assert(not test_paths([(0,1,2), (0,2,3), (0,1,4)], n, t, k))

n = 6
t = 4
k = 1
assert(test_paths(combinations(n, t), n, t, k))
k = 2
assert(test_paths(combinations(n, t), n, t, k))
k = 1
assert(test_paths([(1,2,3,4), (0,3,4,5), (0,1,2,5)], n, t, k))
# has at most 2 common elements with every other

# Check if d is a subset in any element of Cpdiff
def d_included(Cpdiff, d):
    for ci in Cpdiff:
        # if all elements are included
        if set(d).issubset(set(ci)):
            return True
    return False

# Minimum size of intersection between c and all elements of Cp
def mininsect(Cp, c, n):
    m = n
    for cp in Cp:
        m_tmp = n - len(set(c).intersection(set(cp)))
        if m_tmp < m:
            m = m_tmp
    return m

# Generate t-of-n spending paths with up to k non-cooperative
def generate_paths(n, t, k):
    a = set(range(0,n))
    C = combinations(n,t)
    D = combinations(n,k)
    Cp = []
    Cpdiff = []
    for d in D:
        if d_included(Cpdiff, d):
            continue
        # choose some c
        c_candidates = []
        for c in C:
            if not d_included([tuple(a.difference(set(c)))], d):
                continue
            if not c in Cp:
                c_candidates += [(c, mininsect(Cp, c, n))]
        c = max(c_candidates,key=lambda item:item[1])[0]
        Cp += [(c)]
        Cpdiff += [tuple(a.difference(set(c)))]
    return Cp

def cost(Cplen, n, t, k):
    sig = 64
    pk = 32
    branch = 32
    print("- %s-of-%s with up to %s signers non-cooperative" % (t, n, k))
    # + 1 for for the cooperative case
    spending_paths = Cplen + 1
    print("  - Parallel signing sessions:", spending_paths)
    print("  - Everyone in key path cooperative: 1 sig, 1 pk:", sig + pk, "WU")
    # only balanced tree part, i.e. exclude keypath and fallback
    tree_depth = math.ceil(1+math.log(spending_paths-2, 2))
    print("  - Up to %s non-cooperative:         1 sig, 1 pk, %s deep: %s WU" % (k, tree_depth, sig + pk + tree_depth*branch))
    print("  - More than %s non-cooperative:     %s sig, %s pk, 1 deep: %s WU" % (k, t, n, t*sig + n*pk + branch))
    sessions = math.comb(n-1,t-1) # exclude combinations without the signer
    tree_depth = math.ceil(math.log(math.comb(n, t), 2))
    print("  - In Comparison, fully merkleized multisig (%s parallel sessions): 1 sig, 1 pk, %s deep: %s WU" % (sessions, tree_depth, sig + pk + tree_depth*branch))

# Examples
n = 5
t = 3
k = 1
Cp = generate_paths(n,t,k)
cost(len(Cp), n, t, k)
assert(test_paths(Cp, n, t, k))

n = 15
t = 11
k = 2
Cp = generate_paths(n,t,k)
cost(len(Cp), n, t, k)
assert(test_paths(Cp, n, t, k))

n = 20
t = 15
k = 2
Cp = generate_paths(n,t,k)
cost(len(Cp), n, t, k)
assert(test_paths(Cp, n, t, k))

k = 3
Cp = generate_paths(n,t,k)
cost(len(Cp), n, t, k)
assert(test_paths(Cp, n, t, k))
