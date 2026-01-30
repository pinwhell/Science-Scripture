import numpy as np

def compute_entropy(state, indices):
    """
    Compute von Neumann entropy for a subsystem.
    """
    rho = np.tensordot(state, state.conj(), axes=(indices, indices))
    # Simplify for 4-qubit toy model
    # We flatten to density matrix
    rho_dim = int(np.sqrt(rho.size))
    rho = rho.reshape(rho_dim, rho_dim)
    eigvals = np.linalg.eigvalsh(rho)
    eigvals = eigvals[eigvals > 1e-12]
    return -np.sum(eigvals * np.log(eigvals))

from scipy.linalg import expm

def compute_mutual_info(state, idx_a, idx_b):
    """
    Compute Mutual Information I(A:B) = S(A) + S(B) - S(AUB).
    """
    s_a = compute_entropy(state, idx_a)
    s_b = compute_entropy(state, idx_b)
    s_ab = compute_entropy(state, idx_a + idx_b)
    return s_a + s_b - s_ab

def setup_toy_state(L=8):
    """
    A structured state: Product of long-range Bell pairs bridging the half-chains.
    Pairs (i, i + L/2) for i in [0, L/2).
    """
    np.random.seed(42)
    psi = np.zeros(2**L, dtype=complex)
    
    for i in range(2**(L//2)):
        # Config is the bitstring for the first L/2 sites
        config = i
        # Mirror this config to the next L/2 sites to create Bell pairs |00> + |11>
        index = 0
        for bit_pos in range(L//2):
            bit = (config >> bit_pos) & 1
            # Set bit at site 'bit_pos' and 'bit_pos + L/2'
            index |= (bit << bit_pos)
            index |= (bit << (bit_pos + L//2))
        psi[index] = 1.0
        
    psi /= np.linalg.norm(psi)
    return psi.reshape(*(2 for _ in range(L)))

def run_simulation(epsilon=0.1, L=8):
    state = setup_toy_state(L)
    
    # Subsystem A: First half-chain
    sub_a = list(range(L // 2))
    # Relative probe: Site 0 to Site L-1 (farthest distance in pair structure)
    pair_partner = L // 2
    
    s_orig = compute_entropy(state, sub_a)
    # Note: in this setup, I(0:L/2) = 2*S(site 0) because they are a Bell pair
    i_orig = compute_mutual_info(state, [0], [pair_partner])
    
    # Perturbation: State perturbation (δρ injection)
    sigma_x = np.array([[0, 1], [1, 0]])
    sigma_z = np.array([[1, 0], [0, -1]])
    op_inj = sigma_x + 0.5 * sigma_z
    
    # State perturbation on site 0: |psi'> = N (|psi> + epsilon * Op|psi>)
    # site 0 corresponds to the first dimension
    state_pert = state + epsilon * np.tensordot(op_inj, state, axes=(1, 0))
    state_pert /= np.linalg.norm(state_pert)
    
    s_pert = compute_entropy(state_pert, sub_a)
    i_pert = compute_mutual_info(state_pert, [0], [pair_partner])
    
    delta_s = s_pert - s_orig
    delta_i = i_pert - i_orig
    
    return s_orig, i_orig, delta_s, delta_i

def visualize_relational_response(epsilon=0.1, L=8):
    state = setup_toy_state(L)
    
    # Pre-perturbation MI
    mi_orig = np.zeros((L, L))
    for i in range(L):
        for j in range(i+1, L):
            mi_orig[i, j] = compute_mutual_info(state, [i], [j])
    
    # State perturbation (δρ) on site 0
    sigma_x = np.array([[0, 1], [1, 0]])
    sigma_z = np.array([[1, 0], [0, -1]])
    op_inj = sigma_x + 0.5 * sigma_z
    
    state_pert = state + epsilon * np.tensordot(op_inj, state, axes=(1, 0))
    state_pert /= np.linalg.norm(state_pert)
    
    # Post-perturbation MI
    mi_pert = np.zeros((L, L))
    for i in range(L):
        for j in range(i+1, L):
            mi_pert[i, j] = compute_mutual_info(state_pert, [i], [j])
            
    delta_mi = mi_pert - mi_orig
    
    print(f"\nRelational Response Visualization (ΔI mapping) | L={L}, ε={epsilon}")
    print("Change in Mutual Information ΔI(i:j) - Represents 'relational distance proxy' shift due to state perturbation (δρ) at Site 0")
    header = "      " + " ".join([f"{i:5d}" for i in range(L)])
    print(header)
    print("   " + "-" * (L * 6 + 5))
    for i in range(L):
        row = f"{i:2d} | "
        for j in range(L):
            if j <= i:
                row += "      "
            else:
                row += f"{delta_mi[i, j]:+6.3f}"
        print(row)

def demo_scaling():
    L = 8
    print(f" QM-GR Numerical Recovery PoC: Relational Scaling Analysis (L={L}) ")
    print(f"State: Product of distant Bell pairs | δρ state perturbation on Site 0")
    print("-" * 80)
    
    # Baseline
    s0, i0, _, _ = run_simulation(0.0, L)
    print(f"Baseline (ε=0.00) | S_EE (Subsystem A): {s0:.8f} | I(0:{L//2}): {i0:.8f}")
    
    epsilons = [0.05, 0.1, 0.2]
    for eps in epsilons:
        _, _, ds, di = run_simulation(eps, L)
        print(f"ε={eps:.2f} | ΔS_EE = {ds:+.8f} | ΔI(0:{L//2}) = {di:+.8f}")
    
    visualize_relational_response(epsilon=0.1, L=8)

if __name__ == "__main__":
    try:
        demo_scaling()
    except Exception as e:
        print(f"Simulation Error: {e}")
