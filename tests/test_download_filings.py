import hashlib

from scripts import download_filings

CLEAN = b"<html><body><ix:header></ix:header>filing text</body></html>"
SCRIPT = b'<script type="text/javascript"  src="/ab12-cd/_x9"></script>'
INJECTED = CLEAN.replace(b"</body>", SCRIPT + b"</body>")


class FakeResponse:
    def __init__(self, content):
        self.content = content


def fake_get(content):
    return lambda session, url: FakeResponse(content)


def test_strips_the_injected_script_so_the_hash_matches_the_clean_filing(monkeypatch, tmp_path):
    monkeypatch.setattr(download_filings, "polite_get", fake_get(INJECTED))
    dest = tmp_path / "f.htm"
    digest, size = download_filings.download(None, "u", dest)
    assert dest.read_bytes() == CLEAN
    assert digest == hashlib.sha256(CLEAN).hexdigest()
    assert size == len(CLEAN)


def test_leaves_a_clean_filing_unchanged(monkeypatch, tmp_path):
    monkeypatch.setattr(download_filings, "polite_get", fake_get(CLEAN))
    dest = tmp_path / "f.htm"
    digest, _ = download_filings.download(None, "u", dest)
    assert dest.read_bytes() == CLEAN
    assert digest == hashlib.sha256(CLEAN).hexdigest()


def test_keeps_other_scripts(monkeypatch, tmp_path):
    other = CLEAN.replace(b"filing text", b'<script src="https://x.com/a.js"></script>filing text')
    monkeypatch.setattr(download_filings, "polite_get", fake_get(other))
    dest = tmp_path / "f.htm"
    download_filings.download(None, "u", dest)
    assert dest.read_bytes() == other
