import pathlib
from typing import Callable

import click
import panel as pn  # noqa
from click.decorators import FC

from tseda.logging import cli_logger as logger  # noqa
from tseda.logging import log_level

from . import (
    app,  # noqa
    config,  # noqa
    datastore,  # noqa
    model,  # noqa
)
from . import preprocess as preprocess_  # noqa
from .datastore import IndividualsTable  # noqa
from .model import TSModel  # noqa


def log_filter_option(expose_value: bool = False) -> Callable[[FC], FC]:
    """Disable logging filters"""
    return click.option(
        "--no-log-filter",
        default=False,
        is_flag=True,
        expose_value=expose_value,
        help="Do not filter the output log (advanced debugging only)",
    )


@click.group()
def cli():
    """Command line interface for tseda."""


@cli.command()
@click.argument("tszip_path", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False),
    default=None,
    help=(
        "Optional output filename, defaults to tszip_path "
        "with .tseda extension"
    ),
)
@log_filter_option()
@log_level()
def preprocess(tszip_path, output):
    """Preprocess a tskit tree sequence or tszip file, producing a .tseda file.

    Calls preprocess.
    """
    tszip_path = pathlib.Path(tszip_path)
    if output is None:
        output = tszip_path.with_suffix(".tseda")

    preprocess_.preprocess(tszip_path, output, show_progress=True)


@cli.command()
@click.argument("path", type=click.Path(exists=True, dir_okay=False))
@click.option("--port", default=8080, help="Port to serve on")
@click.option(
    "--show/--no-show",
    default=True,
    help="Launch a web-browser showing the app",
)
@click.option(
    "--admin", default=False, is_flag=True, help="Add bokeh admin panel"
)
@log_filter_option()
@log_level()
def serve(path, port, show, admin):
    """Run the tseda datastore server, version based on View base class."""
    tsm = TSModel(path)
    individuals_table, sample_sets_table = datastore.make_tables(tsm)

    logger.info("Starting panel server")
    app_ = app.DataStoreApp(
        datastore=datastore.DataStore(
            tsm=tsm,
            sample_sets_table=sample_sets_table,
            individuals_table=individuals_table,
        ),
        title="TSEda Datastore App",
        views=[IndividualsTable],
    )
    pn.serve(app_.view(), port=port, show=show, verbose=False, admin=admin)


if __name__ == "__main__":
    cli()
