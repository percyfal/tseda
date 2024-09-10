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

Project and package management is done using [rye]. For a good
introduction to rye, see the [postmodern python] blog post.

Use rye to add and remove dependencies from `pyproject.toml`.
Development packages are added by applying the `--dev` flag:

	rye add package
	rye add dev-package --dev
	rye remove package
	rye remove dev-package --dev
	
[rye]: https://rye.astral.sh/
[postmodern python]: https://rdrn.me/postmodern-python/ 

## Virtual environment

rye sets up a virtual environment in `.venv`. You should be able to
activate the environment with `source .venv/bin/activate`. However, if
you have `pyenv` installed you may run into the issue that nothing
seems to load. This is a known issue (see [pyenv issue]). You can
always run programs in the virtual environment with `rye run`, e.g.,

	rye run pytest -v -s

[pyenv issue]: https://github.com/astral-sh/rye/issues/317

## Linting and testing workflow

rye provides support for Python code formatting, linting, and more.
The steps can be run separately

	rye fmt
	rye lint --fix
	rye run check
	rye test
	
Alternativel, you can run the entire toolchain with

	rye run all
