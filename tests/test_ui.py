import time

import panel as pn
from tseda import app
from tseda import datastore
from tseda.vpages import PAGES
from playwright.sync_api import expect

CLICKS = 2


def test_component(page, port, ds):
    url = f"http://localhost:{port}"
    component = app.DataStoreApp(
        datastore=ds,
        title="TSEda Datastore App",
        views=[datastore.IndividualsTable],
    )

    server = pn.serve(component.view, port=port, threaded=True, show=False)
    time.sleep(20)
    page.goto(url)

    page.set_viewport_size({"width": 1920, "height": 1080})

    page.get_by_role("button", name="Sample Sets").click()
    expect(page.get_by_text("New sample set name")).to_be_visible()
    expect(page.get_by_text("predefined")).to_be_visible()

    page.get_by_role("button", name="Individuals").click()
    expect(page.get_by_text("Data modification")).to_be_visible()
    expect(page.get_by_text("Population ID")).to_be_visible()

    page.get_by_role("button", name="Structure").click()
    expect(page.get_by_text("GNN cluster plot")).to_be_visible()

    page.get_by_role("button", name="iGNN").click()
    expect(page.get_by_text("Sample sets table quick view")).to_be_visible()

    page.get_by_role("button", name="Statistics").click()
    expect(
        page.get_by_text("Oneway statistics plotting options")
    ).to_be_visible()

    page.get_by_role("button", name="Trees").click()
    expect(page.get_by_text("Tree plotting options")).to_be_visible()
