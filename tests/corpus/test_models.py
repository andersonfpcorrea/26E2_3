from direito_dados.corpus.models import (
    Annotation,
    Article,
    HierarchyLevel,
    Norm,
    VigenciaStatus,
)


def test_article_citation_is_norm_and_number():
    art = Article(norm_id="CP", number="155", caput="Subtrair...", text="Subtrair...")
    assert art.citation == "CP art. 155"


def test_article_defaults_to_vigente_with_no_annotations():
    art = Article(norm_id="CP", number="121", caput="Matar alguém", text="Matar alguém")
    assert art.status == VigenciaStatus.VIGENTE
    assert art.annotations == []


def test_norm_lookup_by_article_number():
    art = Article(norm_id="CP", number="155", caput="c", text="t")
    norm = Norm(id="CP", title="Código Penal", level=HierarchyLevel.DECRETO_LEI, articles=[art])
    assert norm.article("155") is art
    assert norm.article("999") is None


def test_hierarchy_constituicao_outranks_lei():
    assert HierarchyLevel.CONSTITUICAO.value < HierarchyLevel.LEI_ORDINARIA.value


def test_annotation_is_hashable_frozen():
    a = Annotation(kind="revogado", law_ref="Lei nº 11.106", year=2005)
    assert a.year == 2005
    assert {a, a} == {a}
