"""Static registry of the federal criminal-law microsystem (9 norms)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NormSpec:
    id: str
    title: str
    norm_type: str
    source_url: str
    filename: str


def _spec(id_, title, norm_type, url):
    return NormSpec(id=id_, title=title, norm_type=norm_type, source_url=url,
                    filename=f"{id_}.txt")


NORMS: dict[str, NormSpec] = {
    s.id: s
    for s in [
        _spec("CF", "Constituição Federal de 1988", "constituicao",
              "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm"),
        _spec("CP", "Código Penal (DL 2.848/1940)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del2848compilado.htm"),
        _spec("CPP", "Código de Processo Penal (DL 3.689/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3689compilado.htm"),
        _spec("LEP", "Lei de Execução Penal (7.210/1984)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l7210compilado.htm"),
        _spec("L11343", "Lei de Drogas (11.343/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11343.htm"),
        _spec("L11340", "Lei Maria da Penha (11.340/2006)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/_ato2004-2006/2006/lei/l11340.htm"),
        _spec("L8072", "Crimes Hediondos (8.072/1990)", "lei_ordinaria",
              "https://www.planalto.gov.br/ccivil_03/leis/l8072.htm"),
        _spec("DL3688", "Contravenções Penais (DL 3.688/1941)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del3688.htm"),
        _spec("LINDB", "LINDB (DL 4.657/1942)", "decreto_lei",
              "https://www.planalto.gov.br/ccivil_03/decreto-lei/del4657compilado.htm"),
    ]
}
