"""Genealogical Nearest Neighbors (GNN) analysis, individual haplotype
plots.

Draw GNN proportions for a selected individual over the haplotypes.

"""

import panel as pn

pn.extension()


def page(tsm):
    wip = pn.pane.Alert(
        """## WIP
        
        This page is currently a placeholder!
        """
    )

    md = pn.pane.Markdown(
        """
        ## GNN haplotype plots

        
        """
    )

    sample_id = pn.widgets.TextInput(
        name="Enter sample ID",
        placeholder="Enter a string here...",
        max_length=128,
    )

    md_results = pn.pane.Markdown(
        """## Results

        Bar plot of GNN proportions for the selected individual.
        """
    )

    return pn.Column(wip, md, sample_id, md_results)
