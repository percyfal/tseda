import sys

from tseda.__main__ import cli


def test_main(monkeypatch, tsedafile):
    with monkeypatch.context() as m:
        m.setattr(sys, "argv", [sys.argv[0], str(tsedafile)])


def test_cli(runner, tsedafile):
    result = runner.invoke(cli, [])
    assert result.exit_code == 2
    result = runner.invoke(cli, ["serve", "--no-show"])
    assert result.exit_code == 2
    result = runner.invoke(cli, ["serve", str(tsedafile), "--no-show"])
    assert result.exit_code == 1
