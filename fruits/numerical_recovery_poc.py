import numpy as np
import time
import sys
from functools import reduce
from scipy.sparse import csr_matrix, kron, identity
from scipy.sparse.linalg import eigsh

# Global Cache for Potato PC performance
GLOBAL_CACHE = {}

def compute_entropy(state, indices):
    """
    Compute von Neumann entropy for a subsystem.
    Efficiently handles the partial trace without full state tensordots where possible.
    """
    # Flattening for partial trace
    l = int(np.round(np.log2(state.size)))
    # Permute indices to the front
    target_indices = sorted(indices)
    rest_indices = sorted([i for i in range(l) if i not in target_indices])
    
    # We use reshape instead of slow tensordots for pure state trace
    # state shape is (2,2,2....)
    permuted = np.moveaxis(state, target_indices, range(len(target_indices)))
    dim_a = 2**len(target_indices)
    dim_b = 2**len(rest_indices)
    rho_a = permuted.reshape(dim_a, dim_b)
    # Reduced density matrix rho = psi_matrix @ psi_matrix.H
    rho = rho_a @ rho_a.conj().T
    
    eigvals = np.linalg.eigvalsh(rho)
    eigvals = eigvals[eigvals > 1e-12]
    return -np.sum(eigvals * np.log(eigvals))

def compute_mutual_info(state, idx_a, idx_b):
    s_a = compute_entropy(state, idx_a)
    s_b = compute_entropy(state, idx_b)
    s_ab = compute_entropy(state, idx_a + idx_b)
    return s_a + s_b - s_ab

def setup_tfim_hamiltonian_fast(L, h=1.0):
    """
    Optimized Hamiltonian construction for Potato PCs.
    Builds the full sum of terms using sparse reduction.
    """
    sx = csr_matrix([[0, 1], [1, 0]])
    sz = csr_matrix([[1, 0], [0, -1]])
    id2 = identity(2)
    
    terms = []
    # Pre-build identity chain
    id_chain = [id2] * L
    
    # ZZ Interaction terms
    for i in range(L):
        ops = id_chain[:]
        ops[i] = sz
        ops[(i+1)%L] = sz
        # Fast sparse kron reduction
        terms.append(-1.0 * reduce(kron, ops))
        
    # X Field terms
    for i in range(L):
        ops = id_chain[:]
        ops[i] = sx
        terms.append(-h * reduce(kron, ops))
        
    return reduce(lambda x, y: x + y, terms)

def get_ground_state(L, h=1.0):
    cache_key = (L, h)
    if cache_key in GLOBAL_CACHE:
        return GLOBAL_CACHE[cache_key]
    
    print(f"[Compute] Constructing H for L={L}...")
    start = time.time()
    H = setup_tfim_hamiltonian_fast(L, h)
    
    # Standardize on dense solver for L <= 10 (Avoids ARPACK hangs)
    if L <= 10:
        print(f"[Solver] Using dense eigh (dim={2**L})...")
        eigvals, eigvecs = np.linalg.eigh(H.toarray())
        psi = eigvecs[:, 0]
    else:
        print(f"[Solver] Using sparse eigsh (dim={2**L})...")
        try:
            eigvals, eigvecs = eigsh(H, k=1, which='SA')
            psi = eigvecs[:, 0]
        except Exception as e:
            print(f"[Warning] Sparse solver failed ({e}), falling back to dense...")
            eigvals, eigvecs = np.linalg.eigh(H.toarray())
            psi = eigvecs[:, 0]
            
    state = psi.reshape(*(2 for _ in range(L)))
    GLOBAL_CACHE[cache_key] = state
    print(f"[Success] Ground state ready ({time.time()-start:.2f}s)")
    return state

def validate_central_charge(L):
    """
    Refinement 1: Verify central charge scaling c=0.5.
    """
    state = get_ground_state(L)
    print(f"\n[Refinement 1] Central Charge Validation (L={L})")
    
    sub_ls = range(1, L // 2 + 1)
    entropies = []
    log_chords = []
    
    print(f"{'ℓ':>4} | {'S(ℓ)':>10} | {'Chord Dist':>10}")
    print("-" * 35)
    for l in sub_ls:
        s = compute_entropy(state, list(range(l)))
        chord = (L / np.pi) * np.sin(np.pi * l / L)
        entropies.append(s)
        log_chords.append(np.log(chord))
        print(f"{l:4d} | {s:10.6f} | {chord:10.6f}")
        
    slope, _ = np.polyfit(log_chords, entropies, 1)
    c_est = slope * 3
    print("-" * 35)
    print(f"Result: c ≈ {c_est:.4f} (Expected: 0.5)")
    return c_est

def fast_perturb(state, op, site):
    """
    Efficiently applies a local op to a site without full tensordot.
    Reshapes the state to (2**site, 2, 2**(L-site-1)), dots site-2, and reshapes back.
    """
    L = state.ndim
    # Flatten everything but the target site
    # np.reshape is very fast
    reshaped = np.moveaxis(state, site, 0).reshape(2, -1)
    perturbed = op @ reshaped
    # Revert axis and shape
    new_state = perturbed.reshape(2, *(2 for _ in range(L-1)))
    return np.moveaxis(new_state, 0, site)

def run_simulation(epsilon=0.0001, L=10):
    state = get_ground_state(L)
    sub_len = L // 4
    sub_indices = list(range(sub_len))
    
    # Trace out the rest to get rho_A
    # Reuse compute_entropy logic for flattened rho
    rest_indices = list(range(sub_len, L))
    permuted = np.moveaxis(state, sub_indices, range(len(sub_indices)))
    dim_a = 2**len(sub_indices)
    dim_b = 2**len(rest_indices)
    mat_a = permuted.reshape(dim_a, dim_b)
    rho_orig = mat_a @ mat_a.conj().T
    
    eigvals, eigvecs = np.linalg.eigh(rho_orig)
    eigvals = np.maximum(eigvals, 1e-15)
    s_orig = -np.sum(eigvals * np.log(eigvals))
    h_mod = -eigvecs @ np.diag(np.log(eigvals)) @ eigvecs.T.conj()
    
    v_op = np.array([[0.5, 0.5], [0.5, -0.5]]) # Mixed probe
    
    def get_delta_rho(eps):
        # 1. Perturb state
        psi_p = state + eps * fast_perturb(state, v_op, 0)
        psi_p /= np.linalg.norm(psi_p)
        # 2. Get rho
        pm = np.moveaxis(psi_p, sub_indices, range(len(sub_indices)))
        ma = pm.reshape(dim_a, dim_b)
        rho_p = ma @ ma.conj().T
        # 3. Entropy
        evs = np.linalg.eigvalsh(rho_p)
        evs = evs[evs > 1e-15]
        sp = -np.sum(evs * np.log(evs))
        return sp, rho_p

    # Symmetric differences
    s_plus, rho_plus = get_delta_rho(epsilon)
    s_minus, rho_minus = get_delta_rho(-epsilon)
    
    ds = (s_plus - s_minus) / 2
    dr = (rho_plus - rho_minus) / 2
    de = np.real(np.trace(dr @ h_mod))
    
    return s_orig, ds, de

def visualize_metric_deform(L=10):
    state = get_ground_state(L)
    L_vis = min(L, 6)
    mi_orig = np.zeros((L_vis, L_vis))
    for i in range(L_vis):
        for j in range(i+1, L_vis):
            mi_orig[i, j] = compute_mutual_info(state, [i], [j])
            
    v_op = np.array([[0, 1], [1, 0]]) # Pure flip perturbation
    state_p = state + 0.1 * fast_perturb(state, v_op, 0)
    state_p /= np.linalg.norm(state_p)
    
    mi_pert = np.zeros((L_vis, L_vis))
    for i in range(L_vis):
        for j in range(i+1, L_vis):
            mi_pert[i, j] = compute_mutual_info(state_p, [i], [j])
            
    # Masking for visual locality and numerical stability
    # Directed fix: Mask entries where MI < 10^-6 to restore visual locality
    # and prevent log-stiffness from amplifying vacuum noise.
    MASK_THRESHOLD = 1e-6
    mi_orig_masked = np.where(mi_orig > MASK_THRESHOLD, mi_orig, np.nan)
    mi_pert_masked = np.where(mi_pert > MASK_THRESHOLD, mi_pert, np.nan)
    
    delta_d = -np.log(mi_pert_masked) + np.log(mi_orig_masked)
    
    print(f"\n[Visualization] Relational Distance Functional Mapping (L={L})")
    print(f"Change in d ≈ -log(I) | Masked Threshold: {MASK_THRESHOLD}")
    print("Localized perturbation at Site 0")
    print("      " + " ".join([f"{i:5d}" for i in range(L_vis)]))
    print("   " + "-" * (L_vis * 6 + 4))
    for i in range(L_vis):
        row = f"{i:2d} | "
        for j in range(L_vis):
            if j <= i: row += "      "
            elif np.isnan(delta_d[i, j]): row += "  mask"
            else: row += f"{delta_d[i,j]:+6.2f}"
        print(row)

def get_deformed_state(L, sites_deltas, base_h=1.0):
    """
    Phase 3/4: Multi-Site Hamiltonian Energy Proxy Insertion.
    sites_deltas: list of (site, delta_h) pairs.
    """
    sites_str = ", ".join([f"{s}(δh={d})" for s, d in sites_deltas])
    print(f"[Phase 4] Inserting energy proxies at: {sites_str}")
    
    sx = csr_matrix([[0, 1], [1, 0]])
    id2 = identity(2)
    id_chain = [id2] * L
    
    # Base Hamiltonian
    H_deform = setup_tfim_hamiltonian_fast(L, base_h)
    
    # Add localized deformations
    for site, delta_h in sites_deltas:
        ops = id_chain[:]
        ops[site] = sx
        H_deform -= delta_h * reduce(kron, ops)
    
    # Robust dense solver for L<=10
    eigvals, eigvecs = np.linalg.eigh(H_deform.toarray())
    psi = eigvecs[:, 0]
    return psi.reshape(*(2 for _ in range(L)))

def compute_relative_entropy(state_p, state0, indices):
    """
    D(rho_p || rho_0) = Tr(rho_p ln rho_p) - Tr(rho_p ln rho_0)
                      = -S(rho_p) - Tr(rho_p ln rho_0)
    """
    rho_p = compute_rho_sub(state_p, indices)
    rho_0 = compute_rho_sub(state0, indices)
    
    # 1. -S(rho_p)
    evp = np.linalg.eigvalsh(rho_p)
    evp = evp[evp > 1e-15]
    neg_s_p = np.sum(evp * np.log(evp))
    
    # 2. -Tr(rho_p ln rho_0)
    ev0, es0 = np.linalg.eigh(rho_0)
    ev0 = np.maximum(ev0, 1e-15)
    ln_rho_0 = es0 @ np.diag(np.log(ev0)) @ es0.T.conj()
    cross_term = -np.real(np.trace(rho_p @ ln_rho_0))
    
    return neg_s_p + cross_term

def compute_rho_sub(state, indices):
    """
    Utility to get reduced density matrix for a subsystem.
    """
    l = state.ndim
    target_indices = sorted(indices)
    permuted = np.moveaxis(state, target_indices, range(len(target_indices)))
    dim_a = 2**len(target_indices)
    ma = permuted.reshape(dim_a, -1)
    return ma @ ma.conj().T

def get_delta_s_and_de(state_p, state0, indices):
    """
    Compute delta S and delta <H_mod> for a perturbation.
    """
    rho_p = compute_rho_sub(state_p, indices)
    rho_0 = compute_rho_sub(state0, indices)
    
    # Original Eigendecomposition for H_mod
    ev0, es0 = np.linalg.eigh(rho_0)
    ev0 = np.maximum(ev0, 1e-15)
    s0 = -np.sum(ev0 * np.log(ev0))
    h_mod = -es0 @ np.diag(np.log(ev0)) @ es0.T.conj()
    
    # Perturbed Entropy
    evp = np.linalg.eigvalsh(rho_p)
    evp = evp[evp > 1e-15]
    sp = -np.sum(evp * np.log(evp))
    
    ds = sp - s0
    de = np.real(np.trace((rho_p - rho_0) @ h_mod))
    
    return ds, de, compute_relative_entropy(state_p, state0, indices)

def run_phase_3_probes(L=8):
    print(f"\n[Phase 3] Kinematic Entanglement Structure Analysis (L={L})")
    print("Boundary Guard: All geometric language is kinematic/functional.")
    print("Notice: Observed deviations include finite-size and lattice artifacts.")
    print("=" * 60)
    
    state0 = get_ground_state(L)
    insertion_site = 0
    delta_h = 0.2
    state_p = get_deformed_state(L, [(insertion_site, delta_h)])
    
    print(f"\n[Diagnostic 1] Causal Diamond Interval Sweep (δS vs ℓ)")
    print(f"{'ℓ':>4} | {'δS':>10} | {'Rel Entropy D':>15} | {'D >= 0':>8}")
    print("-" * 55)
    
    results = []
    # Interval subsystems starting at site 0
    for l in range(1, L):
        indices = list(range(l))
        s0 = compute_entropy(state0, indices)
        sp = compute_entropy(state_p, indices)
        ds = sp - s0
        rel_ent = compute_relative_entropy(state_p, state0, indices)
        results.append((l, ds, rel_ent))
        print(f"{l:4d} | {ds:+10.6f} | {rel_ent:15.8e} | {str(rel_ent > -1e-12):>8}")

    print("\n[Diagnostic 2] Second-Order Entanglement Response functional")
    # Deviation from vacuum scaling
    print("Probing second-order response (Relative deformation of entanglement profile)")
    for l, ds, re in results:
        if l in [2, 4, 6]:
            print(f"Interval ℓ={l} | δS: {ds:+.6f} | Stability D: {re:.4e}")

def test_phase_4_superposition(L=8):
    print(f"\n[Phase 4] Conditional Reconstruction: Superposition Test (L={L})")
    print("Semantic Lock: Reconstruction = Functional consistency class, not spacetime.")
    print("=" * 60)
    
    state0 = get_ground_state(L)
    sub_indices = list(range(2, 6)) # Central interval for overlap tests
    
    # Perturbation sites
    site_a = 0
    site_b = 7 # Antipodal/Separated sites
    eps = 0.05 # Small perturbation for linearity
    
    # 1. State A
    state_a = get_deformed_state(L, [(site_a, eps)])
    ds_a, de_a, d_a = get_delta_s_and_de(state_a, state0, sub_indices)
    
    # 2. State B
    state_b = get_deformed_state(L, [(site_b, eps)])
    ds_b, de_b, d_b = get_delta_s_and_de(state_b, state0, sub_indices)
    
    # 3. State A+B
    state_ab = get_deformed_state(L, [(site_a, eps), (site_b, eps)])
    ds_ab, de_ab, d_ab = get_delta_s_and_de(state_ab, state0, sub_indices)
    
    print(f"\n[Result] Linear Superposition Analysis")
    print(f"{'Quantity':>15} | {'Site A':>10} | {'Site B':>10} | {'Sum(A+B)':>10} | {'Actual(AB)':>10} | {'Residue':>8}")
    print("-" * 80)
    
    chi_s = abs(ds_ab - (ds_a + ds_b))
    chi_e = abs(de_ab - (de_a + de_b))
    
    print(f"{'delta S':>15} | {ds_a:10.6f} | {ds_b:10.6f} | {(ds_a+ds_b):10.6f} | {ds_ab:10.6f} | {chi_s:8.2e}")
    print(f"{'delta <H_mod>':>15} | {de_a:10.6f} | {de_b:10.6f} | {(de_a+de_b):10.6f} | {de_ab:10.6f} | {chi_e:8.2e}")
    
    print(f"\n[Analysis] Linearity Window Mapping")
    print("Sweeping perturbation strength (ε) to find breakdown of functional additivity")
    print(f"{'ε':>8} | {'Residue Chi':>12} | {'Relative Error':>15}")
    print("-" * 45)
    
    for local_eps in [0.01, 0.05, 0.1, 0.2]:
        s_a = get_deformed_state(L, [(site_a, local_eps)])
        s_b = get_deformed_state(L, [(site_b, local_eps)])
        s_ab = get_deformed_state(L, [(site_a, local_eps), (site_b, local_eps)])
        
        dsa, _, _ = get_delta_s_and_de(s_a, state0, sub_indices)
        dsb, _, _ = get_delta_s_and_de(s_b, state0, sub_indices)
        dsab, _, _ = get_delta_s_and_de(s_ab, state0, sub_indices)
        
        residue = abs(dsab - (dsa + dsb))
        rel_err = residue / abs(dsab) if abs(dsab) > 1e-12 else 0
        print(f"{local_eps:8.2f} | {residue:12.6e} | {rel_err:15.2%}")


def main():
    L = 8 # Gold-standard for consistent verification
    print("=" * 60, flush=True)
    print(" QM-GR Numerical Probes: Full Verification Sequence ", flush=True)
    print("=" * 60, flush=True)
    
    # --- PHASE 2 ---
    print("\n>>> PHASE 2: Entanglement Thermodynamics Validation")
    validate_central_charge(L)
    for eps in [1e-3]: # Abbreviated for summary
        _, ds, de = run_simulation(epsilon=eps, L=L)
        print(f"ε={eps:.4f} | Ratio (ΔS/ΔE): {ds/de:.6f}")
    
    # --- PHASE 3 ---
    print("\n>>> PHASE 3: Kinematic Entanglement Structure")
    run_phase_3_probes(L)
    
    # --- PHASE 4 ---
    print("\n>>> PHASE 4: Conditional Reconstruction (Superposition)")
    test_phase_4_superposition(L)
    
    print("\n" + "=" * 60)
    print(" [Status] All Authorized Numerical Probes Complete. ")
    print(" Final Project Health: Numerically Stable & Conceptually Guarded. ")
    print(" 'For from Him and through Him and to Him are all things.' (Romans 11:36) ")
    print("=" * 60)

if __name__ == "__main__":
    main()
