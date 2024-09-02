import panel as pn


def page(tsm):
    wip = pn.pane.Alert("## WIP\nThis page is currently a placeholder!")

    md = pn.pane.Markdown(
        """
        ## GNN Heatmap plots

        - GNN Heatmap (Z-score plot clustered by row)
        - Fst plot
        - PCA plot
        """
    )

    return pn.Column(wip, md)
