import pathlib

import click
import daiquiri

daiquiri.setup(level="WARN")  # noqa
import panel as pn  # noqa

from . import app  # noqa
from . import config  # noqa
from . import model  # noqa
from . import datastore  # noqa
from . import preprocess as preprocess_  # noqa
from .datastore import IndividualsTable  # noqa
from .model import TSModel  # noqa


logger = daiquiri.getLogger("tseda")


def setup_logging(log_level, no_log_filter):
    if no_log_filter:
        logger = daiquiri.getLogger("root")
        logger.setLevel(log_level)
    else:
        loggers = ["tseda", "cache", "bokeh", "tornado"]
        for logname in loggers:
            logger = daiquiri.getLogger(logname)
            logger.setLevel(log_level)
        logger = daiquiri.getLogger("bokeh.server.protocol_handler")
        logger.setLevel("CRITICAL")


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
def preprocess(tszip_path, output):
    """Preprocess a tskit tree sequence or tszip file, producing a .tseda file.

    Calls tsbrowse.preprocess.preprocess.
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
@click.option("--log-level", default="INFO", help="Logging level")
@click.option(
    "--no-log-filter",
    default=False,
    is_flag=True,
    help="Do not filter the output log (advanced debugging only)",
)
def serve(path, port, show, log_level, no_log_filter, admin):
    """Run the tseda datastore server, version based on View base class."""
    setup_logging(log_level, no_log_filter)

    tsm = TSModel(path)
    individuals_table, sample_sets_table = datastore.preprocess(tsm)

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
