import time

import panel as pn
from playwright.sync_api import expect

from tseda import app, datastore

CLICKS = 2


def test_component(page, port, ds):
    url = f"http://localhost:{port}"
    component = app.DataStoreApp(
        datastore=ds,
        title="TSEda Datastore App",
        views=[datastore.IndividualsTable],
    )

    _ = pn.serve(component.view, port=port, threaded=True, show=False)
    time.sleep(20)
    page.goto(url)

    page.set_viewport_size({"width": 1920, "height": 1080})

    page.get_by_role("button", name="Individuals & sets").click()
    time.sleep(10)
    expect(page.get_by_text("Geomap").nth(0)).to_be_visible()
    expect(page.get_by_text("Original population ID").nth(0)).to_be_visible()
    expect(page.get_by_text("Create new sample set").nth(0)).to_be_visible()

    page.get_by_role("button", name="Structure").click()
    time.sleep(10)
    expect(page.get_by_text("GNN cluster plot").nth(0)).to_be_visible()
    expect(page.get_by_text("Structure").nth(0)).to_be_visible()

    page.get_by_role("button", name="iGNN").click()
    time.sleep(10)
    expect(
        page.get_by_text("Sample sets table quick view").nth(0)
    ).to_be_visible()

    page.get_by_role("button", name="Statistics").click()
    time.sleep(10)
    expect(
        page.get_by_text("Oneway statistics plotting options").nth(0)
    ).to_be_visible()

    page.get_by_role("button", name="Trees").click()
    time.sleep(10)
    expect(page.get_by_text("Tree plotting options").nth(0)).to_be_visible()
