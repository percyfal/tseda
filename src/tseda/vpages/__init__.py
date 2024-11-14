from . import (
    coalescence,
    coalescence_counts,
    ignn,
    individuals,
    overview,
    sample_sets,
    stats,
    structure,
    trees,
)

PAGES = [
    overview.OverviewPage,
    sample_sets.SampleSetsPage,
    individuals.IndividualsPage,
    structure.StructurePage,
    ignn.IGNNPage,
    stats.StatsPage,
    trees.TreesPage,
    coalescence.CoalescenceRatesPage,
    coalescence_counts.CoalescenceCountsPage,
]

PAGES_MAP = {page.key: page for page in PAGES}
PAGES_BY_TITLE = {page.title: page for page in PAGES}
