from . import (
    gnn,  # noqa: F401
    gnnhaplotype,  # noqa: F401
    overview,  # noqa: F401
    sample_sets,  # noqa: F401
    stats,  # noqa: F401
    structure,  # noqa: F401
    trees,  # noqa: F401
)

PAGES_MAP = {
    "Overview": overview,
    "Sample set editor": sample_sets,
    "Popgen statistics": stats,
    "Structure overview": structure,
    "Individual GNN plots": gnn,
    "Haplotype GNN plots": gnnhaplotype,
    "Trees": trees,
}
