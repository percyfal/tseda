"""Helper module for serving the TSEda app from the command line using panel
serve.

This module is used to serve the TSEda app from the command line using panel
serve. One use case is for development purposes where the --dev argument
enables automated reloading of the app when the source code changes. To launch
the app from the command line run:

$ panel serve --dev --admin --show --args path/to/tszip_file.zip

See
https://panel.holoviz.org/how_to/server/commandline.html
for more
information.
"""

from tseda import app  # noqa
from tseda.datastore import DataStore, make_tables, IndividualsTable  # noqa
from tseda.model import TSModel  # noqa
import daiquiri
import sys

daiquiri.setup(level="WARN")  # noqa
logger = daiquiri.getLogger("tseda")


if len(sys.argv) < 2:
    logger.error(
        "Please provide the path to a TreeSequence file via the --args option."
    )
    sys.exit(1)

path = sys.argv.pop()

tsm = TSModel(path)
individuals_table, sample_sets_table = make_tables(tsm)

ds = DataStore(
    tsm=tsm,
    sample_sets_table=sample_sets_table,
    individuals_table=individuals_table,
)

app_ = app.DataStoreApp(
    datastore=ds,
    title="TSEda Datastore App",
    views=[IndividualsTable],
)

app_.view().servable()
