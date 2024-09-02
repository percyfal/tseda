import panel as pn

pn.extension()


def page(tsm):
    wip = pn.pane.Alert(
        """## WIP
        
        This page is currently a placeholder!
        No computations have yet been implemented.
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

    return pn.Column(wip, md, sample_id)
