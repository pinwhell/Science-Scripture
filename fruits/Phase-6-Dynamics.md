# dynamics of Entanglement: Unitary Evolution and Linearity Breakdown

**Status**: Phase 6 COMPLETE
**Scope**: Unitary Time Evolution ($U = \exp(-iHt)$)
**Constraint**: Zero Metaphysics. Pure Kinematics.

---

## 1. Objective
To test the robustness of the **Scalar Linear Response** hypothesis under unitary time evolution. We investigate whether the "superposition of entanglement" ($\delta S_{AB} \approx \delta S_A + \delta S_B$) persists as the system evolves, or whether quantum scrambling acts as a "non-linearizer."

## 2. Protocol: Exact Unitary Evolution
We employ **Exact Dense Matrix Exponentiation** for a Critical TFIM chain ($L=8$) to avoid Trotterization errors.

**Dynamics**:
$$ |\psi(t)\rangle = e^{-i \hat{H}_0 t} |\psi(0)\rangle $$
- **$\hat{H}_0$**: Critical TFIM Hamiltonian (Integrable reference).
- **Probes**: Local Hamiltonian deformations injected at $t=0$.

## 3. The Linearity Metric
We define the **Dynamic Linearity Error** $\chi(t)$ as the deviation from additivity:
$$ \chi(t) = \left| \delta S_{AB}(t) - (\delta S_A(t) + \delta S_B(t)) \right| $$
where $\delta S(t) = S(\rho(t)) - S(\rho_{vac}(t))$. All entropies are in natural units (**nats**).

> [!NOTE]
> **Normalization**: We track the relative error $\epsilon(t) = \chi(t) / (|\delta S_A| + |\delta S_B|)$ to distinguish physical breakdown from numerical noise.

## 4. Expected Behavior (The Scrambling Hypothesis)
Based on Lieb-Robinson bounds and Operator Spreading theory, we expect:
1.  **Short-Time Linearity ($t < \tau_{scramble}$)**: The response remains additive as long as the "causal cones" of the perturbations do not significantly overlap or scramble.
2.  **Linearity Breakdown ($t > \tau_{scramble}$)**: As operators grow and entanglement becomes global (scrambling), the local linear response approximation must fail.
    *   **Implication**: This failure is **not a bug**. It marks the transition from "linearized field behavior" to "complex quantum chaotic/scrambling behavior."
3.  **Finite-Size Revivals**: In small systems ($L=8$), the breakdown may not be monotonic. Fluctuations and partial linearity recovery at later times ($t > t_{echo}$) should be interpreted as **finite-size recurrences** or operator overlap resonances, not as a fundamental restoration of linearity.

> [!IMPORTANT]
> **Interpretive Guardrail**: Observed deviations from linear additivity at intermediate times reflect finite-size interference and state-dependence of the modular Hamiltonian. They do not indicate a breakdown of unitarity, causality, or quantum linearity.

## 5. Execution Safeguards
The numerical engine includes explicit safeguards:
- **Unitarity Check**: $\| \psi(t) \|^2 = 1.0 \pm 10^{-9}$.
- **Energy Conservation**: $\Delta H(t) = 0$.
- **Finite-Size Warning**: Results are valid only before the "echo time" $t_{echo} \sim L/v_{LR}$.

---

**"Time is the parameter of unitary unfolding, not the generator of being."**
(Internal constraint for interpretive safety).
