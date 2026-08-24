from tmsf.validators.rendered_ratio import rough_html


def test_ratio_bullet_quirk_stays_python_310_compatible():
    # The literal-backslash regex is a parity-preserved no-op. Keep the output
    # identical while avoiding a backslash inside an f-string expression, which
    # is a SyntaxError on Python 3.10.
    assert rough_html("- preserved bullet") == "<li>- preserved bullet</li>"
