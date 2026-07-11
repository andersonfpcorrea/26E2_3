from direito_dados.corpus.registry import NORMS


def test_registry_has_nine_criminal_norms():
    assert len(NORMS) == 9
    assert set(NORMS) == {
        "CF", "CP", "CPP", "LEP", "L11343", "L11340", "L8072", "DL3688", "LINDB"
    }


def test_registry_specs_have_source_and_filename():
    for spec in NORMS.values():
        assert spec.source_url.startswith("http")
        assert spec.filename.endswith(".txt")
        assert spec.norm_type
