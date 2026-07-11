from direito_dados.corpus.models import HierarchyLevel, Norm
from direito_dados.corpus.registry import NORMS, NormSpec
from direito_dados.corpus.loader import load_corpus


def test_all_registry_specs_have_lexml_urn_and_penal_domain():
    for spec in NORMS.values():
        assert spec.urn.startswith("urn:lex:br:federal:"), spec.id
        assert spec.domain == "penal"


def test_norm_carries_urn_and_domain():
    n = Norm(id="CP", title="Código Penal", level=HierarchyLevel.DECRETO_LEI,
             urn="urn:lex:br:federal:decreto.lei:1940-12-07;2848", domain="penal")
    assert n.urn.endswith(";2848")
    assert n.domain == "penal"


def test_domain_is_not_hardcoded_to_criminal():
    # The seam: the SAME model holds any domain, proving 'plug any law' at the schema level.
    n = Norm(id="CDC", title="Código de Defesa do Consumidor",
             level=HierarchyLevel.LEI_ORDINARIA, domain="consumidor")
    assert n.domain == "consumidor"


def test_loaded_norm_propagates_urn_and_domain(tmp_path):
    (tmp_path / "CP.txt").write_text("Art. 1. Texto qualquer.\n", encoding="utf-8")
    spec = NormSpec(id="CP", title="Código Penal", norm_type="decreto_lei",
                    source_url="http://x", filename="CP.txt",
                    urn="urn:lex:br:federal:decreto.lei:1940-12-07;2848", domain="penal")
    corpus = load_corpus(str(tmp_path), specs=[spec])
    loaded = corpus.norm("CP")
    assert loaded.urn.endswith(";2848")
    assert loaded.domain == "penal"
