import numpy as np

"""
Phase U3: Area Flux & First Law
Horizon Kinematics.
STRICT BOUNDARY: No entropy, No temperature, No Hawking concepts.
"""

def define_killing_horizon(metric, killing_vec):
    """
    Identify the location of a Killing horizon.
    A Killing horizon is a null surface where the Killing vector becomes null:
    ξ^μ ξ_μ = 0.
    """
    # Calculation involves checking the norm of the Killing vector
    # In Minkowski coordinates: ξ^μ ξ_μ = -(acceleration * x)^2 + ...
    pass

def compute_surface_gravity(metric, killing_vec):
    """
    Compute the surface gravity κ of the Killing horizon.
    κ is defined purely geometrically as the inaffinity of the null 
    generators ξ of the horizon:
    ∇_ξ ξ^μ = κ ξ^μ on the horizon.
    
    Equivalent covariant form: κ^2 = -0.5 * (∇^μ ξ^ν)(∇_μ ξ_ν)
    
    STRICT BOUNDARY: κ is a geometric constant of the horizon structure.
    No mention of temperature, Hawking radiation, or felt acceleration.
    """
    # For a Rindler wedge with acceleration 'a', κ = a.
    # For a Schwarzschild black hole, κ = 1 / (4M).
    pass
