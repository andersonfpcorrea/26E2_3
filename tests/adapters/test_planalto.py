from direito_dados.adapters import PlanaltoAdapter, SourceAdapter
from direito_dados.corpus.models import HierarchyLevel, Norm, VigenciaStatus
from direito_dados.corpus.registry import NormSpec

SPEC = NormSpec(id="CP", title="Código Penal", norm_type="decreto_lei",
                source_url="http://x", filename="CP.txt",
                urn="urn:lex:br:federal:decreto.lei:1940-12-07;2848", domain="penal")

RAW = """Art. 155. Subtrair coisa alheia móvel:
Pena - reclusão (Redação dada pela Lei nº 13.654, de 2018).

Art. 240. (Revogado pela Lei nº 11.106, de 2005)
"""


def test_planalto_adapter_parses_to_norm_with_identity():
    norm = PlanaltoAdapter().parse(RAW, SPEC)
    assert isinstance(norm, Norm)
    assert norm.urn.endswith(";2848")
    assert norm.domain == "penal"
    assert norm.level == HierarchyLevel.DECRETO_LEI
    assert norm.article("240").status == VigenciaStatus.REVOGADO


def test_planalto_adapter_satisfies_the_protocol():
    assert isinstance(PlanaltoAdapter(), SourceAdapter)


def test_any_custom_adapter_can_satisfy_the_seam():
    # The point of the seam: a NEW source is a new adapter, nothing else changes.
    class FakeAdapter:
        source_name = "fake"

        def fetch(self, spec, raw_dir):
            return f"{raw_dir}/{spec.filename}"

        def parse(self, raw_text, spec):
            return Norm(id=spec.id, title=spec.title,
                        level=HierarchyLevel.LEI_ORDINARIA, urn=spec.urn, domain=spec.domain)

    adapter: SourceAdapter = FakeAdapter()
    assert isinstance(adapter, SourceAdapter)
    assert adapter.parse("", SPEC).domain == "penal"
