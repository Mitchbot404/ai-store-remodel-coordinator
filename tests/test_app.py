from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_ui_create_and_block(tmp_path, monkeypatch):
    monkeypatch.setenv('REMODEL_DB', str(tmp_path / 'ui.sqlite3'))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py')).run()
    assert not app.exception
    for index, value in [(0, 'SYN-02'), (1, 'Demo area'), (2, 'Step 2'), (3, 'demo-user')]:
        app.text_input[index].set_value(value)
    app.text_area[0].set_value('Install sample signage')
    app.button[0].click().run()
    assert not app.exception
    assert 'READY' in app.subheader[0].value
    app.text_input[4].set_value('Material delay')
    app.text_input[6].set_value('demo-user')
    app.text_area[3].set_value('Signage has not arrived')
    app.text_area[4].set_value('Synthetic delivery note: delayed')
    app.button[1].click().run()
    assert not app.exception
    assert 'BLOCKED' in app.subheader[0].value
