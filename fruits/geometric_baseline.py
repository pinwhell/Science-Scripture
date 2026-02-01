import numpy as np

"""
Phase U1: Geometric Baselines
Pure GR Kinematic Primitives. 
No Quantum Imports. No Entropy. No States.
"""

def minkowski_metric(dim=4):
    """
    Return flat spacetime metric η_μν with signature (- + + +).
    """
    g = np.eye(dim)
    g[0, 0] = -1.0
    return g

def rindler_metric(xi, acceleration, dim=4):
    """
    Return the Rindler wedge metric tensor at coordinate xi.
    Metric: ds^2 = -(a*xi)^2 dt^2 + dxi^2 + dy^2 + dz^2
    """
    g = np.eye(dim)
    g[0, 0] = -(acceleration * xi)**2
    return g

def killing_vector(coord, metric_type="minkowski", vector_type="time_translation"):
    """
    Return the components of a normalized Killing vector field generator.
    
    Caveat: This returns the coordinate generator components (e.g., ∂_t). 
    In curved or accelerated frames, physical normalization (g_μν ξ^μ ξ^ν) 
    depends on the local metric. This is a generator, not a four-velocity.
    
    Minkowski: ∂_t is a Killing vector.
    Rindler: ∂_t (boost) is a Killing vector for the wedge.
    """
    if vector_type == "time_translation":
        return np.array([1.0, 0.0, 0.0, 0.0])
    elif vector_type == "boost":
        # In Rindler, the boost generator is the time translation in Rindler coords
        return np.array([1.0, 0.0, 0.0, 0.0])
    else:
        raise ValueError(f"Unknown Killing vector type: {vector_type}")

def boundary_area(radius, dim=4):
    """
    Compute the area-like functional for a codimension-2 spherical surface.
    In 4D Minkowski, this is the surface area of a 2-sphere: 4*pi*r^2.
    """
    if dim == 4:
        return 4 * np.pi * radius**2
    elif dim == 3:
        return 2 * np.pi * radius
    else:
        # General S^(n-2) area formula could be used, but keeping it simple for U1 baselines
        return radius**(dim-2)

def area_variation(radius, delta_r, dim=4):
    """
    Linearized variation δA under a small radial deformation δr.
    δA = (dA/dr) * δr
    For A = 4*pi*r^2, δA = 8*pi*r * δr
    """
    if dim == 4:
        return 8 * np.pi * radius * delta_r
    elif dim == 3:
        return 2 * np.pi * delta_r
    else:
        return (dim-2) * radius**(dim-3) * delta_r

if __name__ == "__main__":
    print("Phase U1: Geometric Baselines Diagnostic")
    r = 1.0
    dr = 0.01
    print(f"Minkowski Area (r={r}): {boundary_area(r):.6f}")
    print(f"Area Variation (dr={dr}): {area_variation(r, dr):.6f}")
