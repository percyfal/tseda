# Contributor guide

Thank you for your interest in improving this project. This project is
open-source under the [MIT license] and welcomes contributions in the
form of bug reports, feature requests, and pull requests.

Here is a list of important resources for contributors:

- [Source Code]
- [Issue Tracker]

[mit license]: https://opensource.org/licenses/MIT
[source code]: https://github.com/percyfal/tseda
[issue tracker]: https://github.com/percyfal/tseda/issues

## Development environment

Project and package management is done using [uv]. For a good
introduction to rye, the predecessor of uv, see the [postmodern
python] blog post. This post explains the motivation to move to a more
modern Python package manager.

Use uv to add and remove dependencies from `pyproject.toml`.
Development packages are added by applying the `--dev` flag:

    uv add package
    uv add dev-package --dev
    uv remove package
    uv remove dev-package --dev

After modifying dependencies, make sure to run `uv sync` to update
the virtual environment.

[uv]: https://docs.astral.sh/uv/
[postmodern python]: https://rdrn.me/postmodern-python/

## Virtual environment

uv sets up a virtual environment in `.venv`. You should be able to
activate the environment with `source .venv/bin/activate`. However, if
you have `pyenv` installed you may run into the issue that nothing
seems to load. This is a known issue (see [pyenv issue]). You can
always run programs in the virtual environment with `uv run`, e.g.,

    uv run pytest -v -s

[pyenv issue]: https://github.com/astral-sh/uv/issues/317

## Linting

Currently uv lacks support for tool chains. The easiest way to run
linting on the codebase is to use [pixi] and run pre-defined tasks.

The basic task to run the linting toolchain is

    pixi run lint

[pixi]: https://pixi.sh/latest/

## Development with small test data set

Development is facilitated by loading the small data set that is
provided and reloading upon code changes:

    uv run python -m tseda serve tests/data/test.trees.tsdate.tseda

Alternatively, you can run the command as `pixi run serve`.

The test data is a modified simulation of the [out of Africa]
demographic model (stdpopsim model `OutOfAfrica_3G09`), amended with
three outgroup species. The geolocations are dummy locations meant to
reflect typical metadata.

[out of africa]: https://github.com/popsim-consortium/stdpopsim/blob/main/stdpopsim/catalog/HomSap/demographic_models.py

## Monitoring resource usage and user behaviour

The `--admin` option will activate the `/admin` panel:

    uv run python -m tseda serve tests/data/test.trees.tsdate.tseda --admin

or

    pixi run admin

If the project is served locally on port 5006, the `/admin` endpoint
would be available at <http://localhost:5006/admin>. See [admin] for
more information.

[admin]: https://panel.holoviz.org/how_to/profiling/admin.html

## Serving the application in development mode

For interactive development, you can serve the app in development mode
with `panel serve`:

    uv run panel serve src/tseda --dev --show --args tests/data/test.trees

or

    pixi run dev

## Adding a new application page

Adding a new application page boils down to adding a new module to
`vpages` and registering that module in `vpages.__init__`.

Assuming your new page is called `MyAnalysis`, start by adding a file
named file `myanalysis.py` to `vpages`. At the very minimum, the file
should contain a class called `MyAnalysisPage` with the following
template:

<!-- markdownlint-disable MD046 -->

```python
import panel as on

from .core import View


class MyAnalysisPage(View):
    key = "myanalysis"
    title = "My Analysis"

    def __panel__(self):
        return on.Column()
```

<!-- markdownlint-enable MD046 -->

In `vpages.__init__.py` add `myanalysis` to the first `import`
statement, and append `myanalysis.MyAnalysisPage` to the `PAGES` list.
This barebones example should produce a new tab in the application.

## Adding a plot to the application page

To add a plot, you should add classes that consume the datastore
object and generate views of the data. The following example shows how
to add a plot of nucleotide diversity.

First we create a new `View`-derived class `NucDivPlot`. The
conversion of data requires some additional imports. The class defines
a `param` object for window size, which will show up as an input box
widget in the `sidebar()` function. The `__panel__()` function sets up
the actual plot.

<!-- markdownlint-disable MD046 -->

```python
import numpy as np
import pandas as pd
import hvplot.pandas
import param

from .core import make_windows
from tseda import config

class NucDivPlot(View):
    window_size = param.Integer(
        default=10000, bounds=(1, None), doc="Size of window"
    )

    @param.depends("window_size")
    def __panel__(self):
        windows = make_windows(self.window_size, self.datastore.tsm.ts.sequence_length)
        data = pd.DataFrame(self.datastore.tsm.ts.diversity(windows=windows))
        data.columns = ["pi"]
        return on.panel(data.hvplot.line(y="pi"))

    def sidebar(self):
        return on.Card(
            self.param.window_size,
            collapsed=True,
            title="Nucleotide diversity plotting options",
            header_background=config.SIDEBAR_BACKGROUND,
            active_header_background=config.SIDEBAR_BACKGROUND,
            styles=config.VCARD_STYLE,
        )
```

<!-- markdownlint-enable MD046 -->

Then we modify the `MyAnalysisPage` class as follows:

<!-- markdownlint-disable MD046 -->

```python
class MyAnalysisPage(View):
    key = "myanalysis"
    title = "My Analysis"
    nucdiv = param.ClassSelector(class_=NucDivPlot)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.nucdiv = NucDivPlot(datastore=self.datastore)

    def __panel__(self):
        return on.Column(self.nucdiv)

    def sidebar(self):
        return on.Column(self.nucdiv.sidebar)
```

<!-- markdownlint-enable MD046 -->

Reload the app and hopefully you will see an added plot and sidebar.

For a more detailed example, see one of the actual modules, e.g.,
`tseda.vpages.stats`.
